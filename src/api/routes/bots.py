from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from ...models.bot import TelegramBot
from ...models.payment import Payment
from ...database.models import db
from ...services.pushinpay_service import PushinPayService
from ...services.telegram_media_service import TelegramMediaService, run_async_media_upload
from ...utils.logger import logger
from ...utils.validators import TelegramValidationService

bots_bp = Blueprint('bots', __name__, url_prefix='/bots')

# Configurações de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg', 'mp4', 'avi', 'mov', 'mkv', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_ogg_audio_file(file):
    """Valida especificamente arquivos de áudio OGG para voice messages do Telegram"""
    if not file or not file.filename:
        return {'valid': False, 'error': 'Nenhum arquivo de áudio fornecido'}
    
    filename = file.filename.lower()
    logger.info(f"🔍 Validando arquivo OGG: {filename}")
    
    # Aceitar apenas OGG e OPUS por extensão
    if not (filename.endswith('.ogg') or filename.endswith('.opus')):
        return {
            'valid': False, 
            'error': f'Apenas arquivos .ogg ou .opus são aceitos. Arquivo enviado: {filename}'
        }
    
    # Verificar MIME type de forma flexível (OGG tem vários MIME types)
    if hasattr(file, 'content_type') and file.content_type:
        valid_mime_types = [
            'audio/ogg',
            'application/ogg', 
            'audio/opus',
            'audio/ogg; codecs=opus',
            'application/octet-stream'  # Alguns browsers usam este para OGG
        ]
        
        mime_ok = any(mime in file.content_type.lower() for mime in valid_mime_types)
        logger.info(f"📋 MIME type: {file.content_type}, Válido: {mime_ok}")
        
        if not mime_ok and file.content_type.strip() != '':
            logger.warning(f"⚠️ MIME type suspeito para OGG: {file.content_type}")
            # Não falha por causa do MIME type, apenas avisa
    
    # Verificar tamanho (20MB para voice messages do Telegram)
    max_size = 20 * 1024 * 1024  # 20MB
    if hasattr(file, 'content_length') and file.content_length:
        if file.content_length > max_size:
            size_mb = file.content_length / 1024 / 1024
            return {
                'valid': False, 
                'error': f'Arquivo muito grande: {size_mb:.1f}MB. Limite: 20MB para voice messages'
            }
        
        if file.content_length == 0:
            return {'valid': False, 'error': 'Arquivo está vazio'}
        
        logger.info(f"📊 Tamanho do arquivo: {file.content_length / 1024 / 1024:.1f}MB")
    
    logger.info("✅ Arquivo OGG passou na validação!")
    return {'valid': True, 'media_type': 'audio', 'file_type': 'ogg_voice'}

@bots_bp.route('/', methods=['GET'])
@login_required
def list_bots():
    """Lista todos os bots do usuário"""
    user_bots = TelegramBot.query.filter_by(user_id=current_user.id).all()
    
    bots_data = []
    for bot in user_bots:
        bots_data.append({
            'id': bot.id,
            'username': bot.bot_username,
            'name': bot.bot_name,
            'status': bot.get_status(),
            'is_active': bot.is_active,
            'is_running': bot.is_running,
            'created_at': bot.created_at.isoformat() if bot.created_at else None
        })
    
    if request.is_json:
        return jsonify({
            'bots': bots_data,
            'total': len(bots_data),
            'can_add_more': current_user.can_add_bot()
        })
    
    return render_template('bots/list.html', bots=bots_data, can_add_more=current_user.can_add_bot())

@bots_bp.route('/validate-token', methods=['POST'])
@login_required
def validate_token():
    """Valida token do bot do Telegram"""
    data = request.get_json() if request.is_json else request.form
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token é obrigatório'}), 400
    
    # Verifica se usuário pode adicionar mais bots
    if not current_user.can_add_bot():
        return jsonify({'error': 'Limite de 30 bots atingido'}), 400
    
    # Verifica se token já está em uso
    existing_bot = TelegramBot.query.filter_by(bot_token=token).first()
    if existing_bot:
        return jsonify({'error': 'Token já está sendo usado por outro bot'}), 400
    
    # Valida token com API do Telegram
    validation_service = TelegramValidationService()
    validation_result = validation_service.validate_bot_token(token)
    
    if not validation_result['valid']:
        return jsonify({'error': validation_result['error']}), 400
    
    return jsonify({
        'valid': True,
        'bot_info': validation_result,
        'message': 'Token válido! Agora configure seu bot.'
    })

@bots_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_bot():
    """Cria um novo bot"""
    if request.method == 'POST':
        try:
            logger.info("🚀 Iniciando criação de bot...")
            
            data = request.get_json() if request.is_json else request.form
            
            token = data.get('token', '').strip()
            name = data.get('name', '').strip()
            welcome_message = data.get('welcome_message', '').strip() or "Olá! Bem-vindo ao meu bot!"
            
            logger.info(f"📋 Dados básicos - Nome: {name}, Token: {token[:10]}...")
            
            # Processa valores PIX
            pix_values_raw = request.form.getlist('pix_values[]') if not request.is_json else data.get('pix_values', [])
            pix_values = []
            for value in pix_values_raw:
                if value and float(value) > 0:
                    pix_values.append(float(value))
            
            # Se não tem valores, usa padrões
            if not pix_values:
                pix_values = [10.0, 20.0, 50.0]
            
            # Processa nomes dos planos
            plan_names_raw = request.form.getlist('plan_names[]') if not request.is_json else data.get('plan_names', [])
            plan_names = []
            for name_item in plan_names_raw:
                if name_item and name_item.strip():
                    plan_names.append(name_item.strip())
            
            # Se não tem nomes, usa padrões
            if not plan_names:
                plan_names = ["Básico", "Premium", "VIP"]
            
            # Processa durações dos planos
            plan_durations_raw = request.form.getlist('plan_duration[]') if not request.is_json else data.get('plan_duration', [])
            plan_durations = []
            for duration in plan_durations_raw:
                if duration and duration.strip():
                    plan_durations.append(duration.strip())
            
            # Se não tem durações, usa padrões
            if not plan_durations:
                plan_durations = ["mensal", "mensal", "mensal"]
            
            import json
            pix_values_json = json.dumps(pix_values)
            plan_names_json = json.dumps(plan_names)
            plan_durations_json = json.dumps(plan_durations)
            
            logger.info(f"💰 Planos configurados: {len(pix_values)} planos")
            
            # Validações básicas
            if not token:
                logger.error("❌ Token não fornecido")
                if request.is_json:
                    return jsonify({'error': 'Token é obrigatório'}), 400
                flash('Token é obrigatório', 'error')
                return render_template('bots/create.html')
            
            # Verifica limite de bots
            if not current_user.can_add_bot():
                logger.error("❌ Limite de bots atingido")
                if request.is_json:
                    return jsonify({'error': 'Limite de 30 bots atingido'}), 400
                flash('Você atingiu o limite de 30 bots', 'error')
                return redirect(url_for('bots.list_bots'))
            
            # Verifica se o token já está sendo usado
            existing_bot = TelegramBot.query.filter_by(bot_token=token).first()
            if existing_bot:
                logger.error("❌ Token já em uso")
                if request.is_json:
                    return jsonify({'error': 'Este token já está sendo usado por outro bot'}), 400
                flash('Este token já está sendo usado por outro bot', 'error')
                return render_template('bots/create.html')
            
            # Valida token novamente
            validation_service = TelegramValidationService()
            validation_result = validation_service.validate_bot_token(token)
            
            if not validation_result['valid']:
                logger.error(f"❌ Token inválido: {validation_result['error']}")
                if request.is_json:
                    return jsonify({'error': validation_result['error']}), 400
                flash(f'Token inválido: {validation_result["error"]}', 'error')
                return render_template('bots/create.html')
            
            # Processa IDs dos grupos
            id_vip = data.get('id_vip', '').strip() if request.is_json else request.form.get('id_vip', '').strip()
            id_logs = data.get('id_logs', '').strip() if request.is_json else request.form.get('id_logs', '').strip()
            
            # Formata IDs dos grupos se fornecidos
            if id_vip:
                id_vip = id_vip.replace('@', '').replace('https://t.me/', '')
                if not id_vip.startswith('-'):
                    id_vip = '-' + id_vip
            else:
                id_vip = None
                
            if id_logs:
                id_logs = id_logs.replace('@', '').replace('https://t.me/', '')
                if not id_logs.startswith('-'):
                    id_logs = '-' + id_logs
            else:
                id_logs = None

            logger.info(f"👥 Grupos - VIP: {id_vip}, Logs: {id_logs}")

            # Verifica arquivos de mídia ANTES de criar o bot
            media_file = request.files.get('welcome_image')
            audio_file = request.files.get('welcome_audio')
            
            logger.info(f"📁 Arquivos enviados:")
            logger.info(f"   - Mídia: {media_file.filename if media_file else 'Nenhum'}")
            logger.info(f"   - Áudio: {audio_file.filename if audio_file else 'Nenhum'}")
            
            # Validação de múltiplos arquivos
            if media_file and audio_file:
                logger.warning("⚠️ DOIS ARQUIVOS DETECTADOS - Possível problema!")
                if media_file.content_length and audio_file.content_length:
                    total_size = media_file.content_length + audio_file.content_length
                    logger.info(f"📊 Tamanho total dos arquivos: {total_size / 1024 / 1024:.1f}MB")
                    
                    if total_size > 50 * 1024 * 1024:  # 50MB total
                        logger.error("❌ Arquivos muito grandes juntos")
                        if request.is_json:
                            return jsonify({'error': 'Tamanho total dos arquivos excede 50MB'}), 400
                        flash('Tamanho total dos arquivos muito grande', 'error')
                        return render_template('bots/create.html')

            # Cria o bot PRIMEIRO
            logger.info("💾 Criando registro do bot no banco de dados...")
            
            # Extrair username real do bot (com @)
            bot_real_username = validation_result.get('username', '')
            if bot_real_username and not bot_real_username.startswith('@'):
                bot_real_username = f"@{bot_real_username}"
            
            logger.info(f"🤖 Username real do bot: {bot_real_username}")
            logger.info(f"📝 Nome do bot: {validation_result.get('first_name', '')}")
            logger.info(f"🔑 Bot ID: {validation_result.get('id', '')}")
            
            bot = TelegramBot(
                bot_token=token,
                bot_username=bot_real_username or None,  # Username com @ (ex: @meubot)
                bot_name=name or validation_result.get('first_name', ''),  # Nome amigável
                welcome_message=welcome_message,
                pix_values=pix_values_json,
                plan_names=plan_names_json,
                plan_duration=plan_durations_json,
                id_vip=id_vip,
                id_logs=id_logs,
                user_id=current_user.id,
                is_active=True
            )
            
            logger.info("📋 Dados do bot a ser criado:")
            logger.info(f"   - Token: {token[:10]}...")
            logger.info(f"   - Username: {bot.bot_username}")
            logger.info(f"   - Name: {bot.bot_name}")
            logger.info(f"   - User ID: {bot.user_id}")
            logger.info(f"   - VIP Group: {bot.id_vip}")
            logger.info(f"   - Logs Group: {bot.id_logs}")
            
            # Adiciona ao banco e força commit para obter ID
            try:
                db.session.add(bot)
                db.session.flush()  # Obtém ID sem fazer commit completo
                logger.info(f"✅ Bot adicionado à sessão do banco")
                
                bot_id = bot.id
                logger.info(f"✅ Bot criado no banco com ID: {bot_id}")
                
                if not bot_id:
                    raise Exception("ID do bot não foi gerado após flush()")
                    
            except Exception as db_error:
                logger.error(f"❌ ERRO ao salvar bot no banco: {db_error}")
                logger.error(f"❌ Tipo do erro: {type(db_error)}")
                db.session.rollback()
                raise Exception(f"Falha ao salvar bot no banco de dados: {str(db_error)}")

            # AGORA processa os arquivos com o ID do bot
            media_processed = False
            audio_processed = False
            
            # IMPORTANTE: Processa os arquivos em SEQUÊNCIA para evitar conflitos no Telegram API
            # Processa MÍDIA (imagem/vídeo) primeiro
            if media_file and media_file.filename and allowed_file(media_file.filename):
                logger.info(f"🖼️ INICIANDO processamento de mídia: {media_file.filename}")
                logger.info(f"📊 Tamanho: {getattr(media_file, 'content_length', 'desconhecido')} bytes")
                logger.info(f"📋 Tipo MIME: {getattr(media_file, 'content_type', 'desconhecido')}")
                
                try:
                    # Reset file pointer para garantir leitura desde o início
                    media_file.seek(0)
                    logger.info("📍 File pointer resetado para posição 0")
                    
                    # Criar serviço de mídia
                    logger.info("🔧 Criando TelegramMediaService...")
                    media_service = TelegramMediaService(bot.bot_token)
                    logger.info("✅ TelegramMediaService criado com sucesso")
                    
                    # Validar arquivo
                    logger.info("🔍 Iniciando validação do arquivo de mídia...")
                    validation = media_service.validate_media_file(media_file)
                    logger.info(f"📋 Resultado da validação: {validation}")
                    
                    if validation['valid']:
                        logger.info(f"✅ Mídia validada com sucesso como: {validation['media_type']}")
                        
                        # Reset novamente antes de criar arquivo temporário
                        media_file.seek(0)
                        logger.info("📍 File pointer resetado novamente antes de criar temp file")
                        
                        # Criar arquivo temporário
                        logger.info("📂 Criando arquivo temporário...")
                        temp_path = media_service.create_temp_file(media_file, prefix=f"bot_{bot_id}_img_")
                        logger.info(f"✅ Arquivo temporário criado em: {temp_path}")
                        
                        # Verificar se arquivo temporário foi criado corretamente
                        import os
                        if os.path.exists(temp_path):
                            file_size = os.path.getsize(temp_path)
                            logger.info(f"📊 Arquivo temporário verificado - Tamanho: {file_size} bytes")
                        else:
                            logger.error(f"❌ ERRO: Arquivo temporário não foi criado: {temp_path}")
                            raise Exception("Falha ao criar arquivo temporário")
                        
                        try:
                            if bot.id_logs:
                                logger.info(f"📤 INICIANDO upload de mídia para grupo: {bot.id_logs}")
                                logger.info(f"🤖 Token do bot: {bot.bot_token[:10]}...")
                                logger.info(f"📁 Caminho do arquivo: {temp_path}")
                                logger.info(f"🏷️ Tipo de mídia: {validation['media_type']}")
                                
                                # Delay inicial para evitar rate limiting
                                import time
                                time.sleep(1)
                                logger.info("⏳ Delay de 1 segundo aplicado")
                                
                                # Determinar o tipo correto para o Telegram API
                                telegram_media_type = validation['media_type']
                                
                                # Para vídeos, garantir que o tipo está correto
                                if validation['media_type'] == 'video':
                                    telegram_media_type = 'video'
                                elif validation['media_type'] == 'photo':
                                    telegram_media_type = 'photo'
                                
                                logger.info(f"🎬 Tipo final para Telegram: {telegram_media_type}")
                                
                                # ESTE É O PONTO CRÍTICO - vamos logar tudo sobre o upload
                                logger.info("🚀 CHAMANDO run_async_media_upload...")
                                file_id = run_async_media_upload(
                                    bot.bot_token,
                                    temp_path,
                                    bot.id_logs,
                                    bot_id,
                                    telegram_media_type  # Usar o tipo correto
                                )
                                logger.info(f"📥 RETORNO do run_async_media_upload: {file_id}")
                                logger.info(f"📋 Tipo do retorno: {type(file_id)}")
                                
                                if file_id and file_id != "None" and str(file_id).strip():
                                    logger.info(f"🎉 Upload bem-sucedido! File ID recebido: {file_id}")
                                    
                                    # Salva no campo correto baseado no tipo
                                    if validation['media_type'] == 'video':
                                        bot.welcome_video_file_id = file_id
                                        logger.info(f"💾 SALVANDO vídeo file_id no campo welcome_video_file_id: {file_id}")
                                    else:  # photo/image
                                        bot.welcome_image_file_id = file_id
                                        logger.info(f"💾 SALVANDO imagem file_id no campo welcome_image_file_id: {file_id}")
                                    
                                    # Limpa referência local
                                    bot.welcome_image = None
                                    media_processed = True
                                    
                                    # COMMIT IMEDIATO para salvar file_id da mídia
                                    logger.info("💾 Fazendo flush para salvar file_id no banco...")
                                    db.session.flush()
                                    logger.info("✅ MÍDIA SALVA NO BANCO com sucesso!")
                                    
                                    # Verificar se realmente foi salvo
                                    logger.info(f"🔍 Verificação pós-save:")
                                    logger.info(f"   - welcome_image_file_id: {bot.welcome_image_file_id}")
                                    logger.info(f"   - welcome_video_file_id: {bot.welcome_video_file_id}")
                                    logger.info(f"   - welcome_image (legado): {bot.welcome_image}")
                                    
                                else:
                                    logger.error(f"❌ UPLOAD FALHOU! File ID vazio ou inválido: '{file_id}'")
                                    logger.error(f"❌ Tipo do file_id retornado: {type(file_id)}")
                                    logger.error(f"❌ Representação string: '{str(file_id)}'")
                                    raise Exception(f"Upload falhou - file_id inválido: '{file_id}'")
                                    
                            else:
                                logger.warning("⚠️ Sem grupo de logs - salvando mídia localmente")
                                # Salvar localmente quando não tem grupo
                                media_file.seek(0)
                                filename = secure_filename(media_file.filename)
                                filename = f"bot_{bot_id}_media_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                file_path = os.path.join(UPLOAD_FOLDER, filename)
                                media_file.save(file_path)
                                bot.welcome_image = file_path
                                media_processed = True
                                logger.info(f"💾 Mídia salva localmente: {file_path}")
                                
                        except Exception as upload_error:
                            logger.error(f"❌ EXCEÇÃO no upload de mídia: {upload_error}")
                            logger.error(f"❌ Tipo da exceção: {type(upload_error)}")
                            logger.error(f"❌ Args da exceção: {upload_error.args}")
                            
                            # Fallback: salvar localmente
                            try:
                                logger.info("🔄 Tentando fallback para salvamento local...")
                                media_file.seek(0)
                                filename = secure_filename(media_file.filename)
                                filename = f"bot_{bot_id}_media_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                file_path = os.path.join(UPLOAD_FOLDER, filename)
                                media_file.save(file_path)
                                bot.welcome_image = file_path
                                media_processed = True
                                logger.info(f"✅ Mídia salva como fallback local: {file_path}")
                            except Exception as fallback_error:
                                logger.error(f"❌ FALHA no fallback também: {fallback_error}")
                                media_processed = False
                            

                        finally:
                            # Sempre limpa arquivo temporário
                            try:
                                if 'temp_path' in locals() and temp_path:
                                    media_service.cleanup_temp_file(temp_path)
                                    logger.info("🧹 Arquivo temporário de mídia limpo")
                            except Exception as cleanup_error:
                                logger.error(f"⚠️ Erro ao limpar temp file: {cleanup_error}")
                                
                    else:
                        logger.error(f"❌ Mídia INVÁLIDA: {validation.get('error', 'Erro desconhecido')}")
                        logger.error(f"❌ Detalhes da validação: {validation}")
                        media_processed = False
                        
                except Exception as e:
                    logger.error(f"❌ ERRO CRÍTICO processando mídia: {e}")
                    logger.error(f"❌ Tipo do erro crítico: {type(e)}")
                    logger.error(f"❌ Stack trace: {str(e)}")
                    media_processed = False
            else:
                logger.info("📷 Nenhum arquivo de mídia fornecido ou arquivo inválido")
                if media_file:
                    logger.info(f"   - Filename: {media_file.filename}")
                    logger.info(f"   - Allowed: {allowed_file(media_file.filename) if media_file.filename else 'N/A'}")

            # PAUSA OBRIGATÓRIA entre uploads para evitar conflitos no Telegram
            if media_processed and audio_file:
                logger.info("⏳ Aguardando 3 segundos antes de processar áudio...")
                import time
                time.sleep(3)
            
            # Processa ÁUDIO após a mídia
            if audio_file and audio_file.filename and allowed_file(audio_file.filename):
                logger.info(f"🎵 Processando áudio: {audio_file.filename}")
                logger.info(f"📊 Tamanho do áudio: {getattr(audio_file, 'content_length', 'desconhecido')} bytes")
                
                try:
                    # Reset file pointer
                    audio_file.seek(0)
                    
                    # Validação específica para OGG antes de processar
                    if audio_file.filename.lower().endswith('.ogg'):
                        logger.info("🔍 Detectado arquivo OGG - usando validação específica")
                        validation = validate_ogg_audio_file(audio_file)
                    else:
                        # NOVA INSTÂNCIA do serviço para evitar conflitos
                        audio_service = TelegramMediaService(bot.bot_token)
                        validation = audio_service.validate_media_file(audio_file)
                    
                    if validation['valid'] and validation['media_type'] == 'audio':
                        logger.info("✅ Áudio validado")
                        
                        # Reset novamente antes de criar arquivo temporário
                        audio_file.seek(0)
                        
                        # Criar serviço de mídia se não foi criado
                        if 'audio_service' not in locals():
                            audio_service = TelegramMediaService(bot.bot_token)
                        
                        temp_path = audio_service.create_temp_file(audio_file, prefix=f"bot_{bot_id}_audio_")
                        logger.info(f"📂 Arquivo temporário de áudio criado: {temp_path}")
                        
                        try:
                            if bot.id_logs:
                                logger.info(f"📤 ENVIANDO ÁUDIO para grupo: {bot.id_logs}")
                                
                                # Delay adicional para áudio
                                import time
                                time.sleep(2)
                                
                                # Para OGG, especificar que é voice message
                                media_type = 'voice' if audio_file.filename.lower().endswith('.ogg') else 'audio'
                                
                                file_id = run_async_media_upload(
                                    bot.bot_token,
                                    temp_path,
                                    bot.id_logs,
                                    bot_id,
                                    media_type
                                )
                                
                                logger.info(f"📥 RESULTADO upload áudio: {file_id}")
                                
                                if file_id and file_id != "None" and str(file_id).strip():
                                    bot.welcome_audio_file_id = file_id
                                    bot.welcome_audio = None
                                    audio_processed = True
                                    
                                    # COMMIT IMEDIATO para salvar file_id do áudio
                                    db.session.flush()
                                    logger.info("✅ ÁUDIO SALVO NO BANCO com sucesso!")
                                    
                                    # Verificar se realmente foi salvo
                                    logger.info(f"🔍 Verificação pós-save áudio:")
                                    logger.info(f"   - welcome_audio_file_id: {bot.welcome_audio_file_id}")
                                    logger.info(f"   - welcome_audio (legado): {bot.welcome_audio}")
                                    
                                else:
                                    logger.error("❌ Upload de áudio retornou file_id vazio!")
                                    raise Exception("Upload de áudio falhou - file_id vazio")
                                    
                            else:
                                logger.warning("⚠️ Sem grupo de logs - salvando áudio localmente")
                                # Salvar áudio localmente
                                audio_file.seek(0)
                                filename = secure_filename(audio_file.filename)
                                filename = f"bot_{bot_id}_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                file_path = os.path.join(UPLOAD_FOLDER, filename)
                                audio_file.save(file_path)
                                bot.welcome_audio = file_path
                                audio_processed = True
                                
                        except Exception as audio_upload_error:
                            logger.error(f"❌ ERRO no upload de áudio: {audio_upload_error}")
                            # Fallback: salvar áudio localmente
                            audio_file.seek(0)
                            filename = secure_filename(audio_file.filename)
                            filename = f"bot_{bot_id}_audio_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                            file_path = os.path.join(UPLOAD_FOLDER, filename)
                            audio_file.save(file_path)
                            bot.welcome_audio = file_path
                            audio_processed = True
                            logger.info(f"💾 Áudio salvo como fallback local")
                            
                        finally:
                            # Sempre limpa arquivo temporário
                            try:
                                audio_service.cleanup_temp_file(temp_path)
                                logger.info("🧹 Arquivo temporário de áudio limpo")
                            except:
                                pass
                                
                    else:
                        logger.error(f"❌ Áudio inválido: {validation.get('error')}")
                        
                except Exception as e:
                    logger.error(f"❌ ERRO CRÍTICO processando áudio: {e}")
                    audio_processed = False

            # Log final detalhado
            logger.info(f"📊 RESUMO DO PROCESSAMENTO:")
            logger.info(f"   🖼️ Mídia processada: {media_processed}")
            logger.info(f"   🎵 Áudio processado: {audio_processed}")
            logger.info(f"   💾 Image File ID no banco: {getattr(bot, 'welcome_image_file_id', None)}")
            logger.info(f"   💾 Audio File ID no banco: {getattr(bot, 'welcome_audio_file_id', None)}")
            logger.info(f"   💾 Video File ID no banco: {getattr(bot, 'welcome_video_file_id', None)}")
            
            # Se ambos falharam, reporta
            if media_file and audio_file and not media_processed and not audio_processed:
                logger.error("❌ AMBOS OS ARQUIVOS FALHARAM NO UPLOAD!")
                flash('Erro ao processar mídia e áudio. Verifique os arquivos e tente novamente.', 'error')
            elif media_file and not media_processed:
                logger.error("❌ FALHA NO UPLOAD DA MÍDIA!")
                flash('Erro ao processar imagem/vídeo, mas áudio foi salvo.', 'warning')
            elif audio_file and not audio_processed:
                logger.error("❌ FALHA NO UPLOAD DO ÁUDIO!")
                flash('Erro ao processar áudio, mas imagem foi salva.', 'warning')

            # Verifica se usuário tem token PushinPay
            if not current_user.pushinpay_token:
                logger.warning("⚠️ Usuário sem token PushinPay")
                flash('Configure seu token PushinPay no perfil antes de criar bots.', 'error')
                return redirect(url_for('auth.profile'))

            # Bot é criado diretamente ativo
            bot.is_active = True
            
            # COMMIT FINAL - salva tudo no banco
            logger.info("💾 Salvando bot final no banco de dados...")
            db.session.commit()
            logger.info("✅ Bot salvo com sucesso no banco de dados!")

            # Inicia o bot Telegram automaticamente
            logger.info("🚀 Iniciando bot no Telegram...")
            from ...services.telegram_bot_manager import bot_manager
            import asyncio
            import threading

            def start_bot_async():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(bot_manager.start_bot(bot))
                    
                    if success:
                        bot.is_running = True
                        bot.last_activity = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"✅ Bot {bot.bot_name} iniciado com sucesso!")
                    else:
                        logger.error(f"❌ Falha ao iniciar bot {bot.bot_name}")
                        
                except Exception as e:
                    logger.error(f"❌ Erro ao iniciar bot {bot.bot_name}: {e}")

            bot_thread = threading.Thread(target=start_bot_async, daemon=True)
            bot_thread.start()
            
            # Pequeno delay para o bot iniciar
            import time
            time.sleep(2)

            logger.info("🎉 Processo de criação de bot concluído!")

            if request.is_json:
                return jsonify({
                    'success': True,
                    'bot_id': bot.id,
                    'message': 'Bot criado e ativado com sucesso! 🚀',
                    'media_processed': media_processed,
                    'audio_processed': audio_processed
                }), 201

            flash('Bot criado com sucesso e está sendo iniciado! 🚀', 'success')
            return redirect(url_for('bots.list_bots'))

        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO na criação do bot: {e}")
            logger.error(f"❌ Stack trace: {str(e)}")
            db.session.rollback()
            
            if request.is_json:
                return jsonify({'error': f'Erro ao criar bot: {str(e)}'}), 500
            flash(f'Erro ao criar bot: {str(e)}', 'error')
            return render_template('bots/create.html')

    return render_template('bots/create.html')


@bots_bp.route('/payment/<int:bot_id>', methods=['GET'])
@login_required
def payment_status(bot_id):
    """Exibe status do pagamento do bot"""
    bot = TelegramBot.query.filter_by(id=bot_id, user_id=current_user.id).first()
    if not bot:
        flash('Bot não encontrado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Busca pagamento pendente
    payment = Payment.query.filter_by(bot_id=bot_id).filter(Payment.status == 'pending').first()
    if not payment:
        flash('Pagamento não encontrado.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('bots/payment.html', bot=bot, payment=payment)


@bots_bp.route('/api/payments/check/<int:bot_id>', methods=['GET'])
@login_required
def check_payment_status_api(bot_id):
    """API para verificar status do pagamento"""
    bot = TelegramBot.query.filter_by(id=bot_id, user_id=current_user.id).first()
    if not bot:
        return jsonify({'error': 'Bot não encontrado'}), 404
    
    # Busca pagamento pendente
    payment = Payment.query.filter_by(bot_id=bot_id).filter(Payment.status == 'pending').first()
    if not payment:
        return jsonify({'paid': False, 'status': 'no_payment'})
    
    # Verifica com a PushinPay se necessário
    if current_user.pushinpay_token:
        pix_service = PushinPayService()
        try:
            status_result = pix_service.check_payment_status(
                current_user.pushinpay_token,
                payment.pix_code
            )
            
            if status_result.get('paid'):
                # Confirma pagamento localmente
                payment.status = 'completed'
                payment.paid_at = datetime.utcnow()
                bot.is_active = True
                db.session.commit()
                
                return jsonify({'paid': True, 'status': 'confirmed'})
                
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento: {e}")
    
        return jsonify({'paid': False, 'status': 'pending'})

@bots_bp.route('/edit/<slug>', methods=['GET', 'POST'])
@login_required
def edit_bot(slug):
    """Edita um bot através da slug única"""
    # Busca o bot pela slug (que é o ID do bot)
    try:
        bot_id = int(slug)
        bot = TelegramBot.query.get_or_404(bot_id)
    except ValueError:
        flash('Bot não encontrado.', 'error')
        return redirect(url_for('bots.list_bots'))
    
    # Verifica se o usuário tem permissão (dono do bot ou admin)
    if bot.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este bot.', 'error')
        return redirect(url_for('bots.list_bots'))
    
    if request.method == 'POST':
        try:
            # Atualiza informações básicas
            bot.bot_name = request.form.get('name', '').strip()
            bot.bot_token = request.form.get('token', '').strip()
            bot.welcome_message = request.form.get('welcome_message', '').strip()
            
            # Atualiza valores PIX, nomes dos planos e durações
            pix_values = []
            plan_names = []
            plan_durations = []
            
            for value in request.form.getlist('pix_values[]'):
                if value and float(value) > 0:
                    pix_values.append(float(value))
            
            for name in request.form.getlist('plan_names[]'):
                if name and name.strip():
                    plan_names.append(name.strip())
            
            for duration in request.form.getlist('plan_duration[]'):
                if duration and duration.strip():
                    plan_durations.append(duration.strip())
            
            bot.pix_values = pix_values
            bot.plan_names = plan_names
            bot.plan_duration = plan_durations
            
            # Atualiza IDs dos grupos
            id_vip = request.form.get('id_vip', '').strip()
            id_logs = request.form.get('id_logs', '').strip()
            
            if id_vip:
                # Remove @ ou qualquer prefixo e mantém apenas números e -
                id_vip = id_vip.replace('@', '').replace('https://t.me/', '')
                if not id_vip.startswith('-'):
                    id_vip = '-' + id_vip
                bot.id_vip = id_vip
            else:
                bot.id_vip = None
                
            if id_logs:
                # Remove @ ou qualquer prefixo e mantém apenas números e -
                id_logs = id_logs.replace('@', '').replace('https://t.me/', '')
                if not id_logs.startswith('-'):
                    id_logs = '-' + id_logs
                bot.id_logs = id_logs
            else:
                bot.id_logs = None
            
            # Processa upload de imagem de boas-vindas usando Telegram
            if 'welcome_image' in request.files:
                file = request.files['welcome_image']
                if file and file.filename and allowed_file(file.filename):
                    try:
                        # Cria serviço de mídia
                        media_service = TelegramMediaService(bot.bot_token)
                        
                        # Valida arquivo
                        validation = media_service.validate_media_file(file)
                        
                        # CORREÇÃO: Aceita tanto photo quanto video
                        if validation['valid'] and validation['media_type'] in ['photo', 'video']:
                            # Cria arquivo temporário
                            temp_path = media_service.create_temp_file(file, prefix=f"bot_{bot.id}_img_")
                            
                            try:
                                # Faz upload para Telegram se tiver grupo de logs configurado
                                if bot.id_logs:
                                    # Usa o tipo correto baseado na validação
                                    upload_type = validation['media_type']  # 'photo' ou 'video'
                                    
                                    file_id = run_async_media_upload(
                                        bot.bot_token,
                                        temp_path,
                                        bot.id_logs,
                                        bot.id,
                                        upload_type  # Usar o tipo correto
                                    )
                                    
                                    if file_id:
                                        # Salva no campo correto baseado no tipo
                                        if validation['media_type'] == 'video':
                                            bot.welcome_video_file_id = file_id
                                            # Limpa outros campos de mídia
                                            bot.welcome_image_file_id = None
                                            logger.info(f"✅ Vídeo enviado para Telegram. File ID: {file_id}")
                                        else:  # photo
                                            bot.welcome_image_file_id = file_id
                                            # Limpa outros campos de mídia
                                            bot.welcome_video_file_id = None
                                            logger.info(f"✅ Imagem enviada para Telegram. File ID: {file_id}")
                                        
                                        # Remove referência ao arquivo local antigo se existir
                                        bot.welcome_image = None
                                    else:
                                        logger.warning("⚠️  Falha no upload para Telegram, mantendo arquivo local")
                                        # Fallback: salva localmente se o upload falhar
                                        filename = secure_filename(file.filename)
                                        filename = f"bot_{bot.id}_welcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                                        file.save(file_path)
                                        bot.welcome_image = file_path
                                else:
                                    logger.warning("⚠️  Grupo de logs não configurado, salvando localmente")
                                    # Fallback: salva localmente se não tiver grupo configurado
                                    filename = secure_filename(file.filename)
                                    filename = f"bot_{bot.id}_welcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                                    file.save(file_path)
                                    bot.welcome_image = file_path
                            finally:
                                media_service.cleanup_temp_file(temp_path)
                        else:
                            flash(f'Erro na validação da mídia: {validation.get("error", "Arquivo inválido")}. Tipos suportados: imagens e vídeos.', 'error')
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar mídia: {e}")
                        flash('Erro ao processar mídia. Tente novamente.', 'error')

            if 'welcome_audio' in request.files:
                file = request.files['welcome_audio']
                if file and allowed_file(file.filename):
                    try:
                        media_service = TelegramMediaService(bot.bot_token)
                        validation = media_service.validate_media_file(file)
                        if validation['valid'] and validation['media_type'] == 'audio':
                            temp_path = media_service.create_temp_file(file, prefix=f"bot_{bot.id}_audio_")
                            try:
                                if bot.id_logs:
                                    file_id = run_async_media_upload(
                                        bot.bot_token,
                                        temp_path,
                                        bot.id_logs,
                                        bot.id,
                                        'audio'
                                    )
                                    if file_id:
                                        bot.welcome_audio_file_id = file_id
                                        bot.welcome_audio = None
                                        logger.info(f"✅ Áudio enviado para Telegram. File ID: {file_id}")
                                    else:
                                        logger.warning("⚠️  Falha no upload para Telegram, mantendo arquivo local")
                                        # Fallback: salva localmente se o upload falhar
                                        filename = secure_filename(file.filename)
                                        filename = f"bot_{bot.id}_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                                        file.save(file_path)
                                        bot.welcome_audio = file_path
                                else:
                                    logger.warning("⚠️  Grupo de logs não configurado, salvando localmente")
                                    # Fallback: salva localmente se não tiver grupo configurado
                                    filename = secure_filename(file.filename)
                                    filename = f"bot_{bot.id}_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                                    file.save(file_path)
                                    bot.welcome_audio = file_path
                            finally:
                                media_service.cleanup_temp_file(temp_path)
                        else:
                            flash(f'Erro na validação do áudio: {validation.get("error", "Arquivo inválido")}', 'error')
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar áudio: {e}")
                        flash('Erro ao processar áudio. Tente novamente.', 'error')

            db.session.commit()
            
            flash('Bot atualizado com sucesso!', 'success')
            logger.info(f"Bot {bot.bot_name} (ID: {bot.id}) atualizado pelo usuário {current_user.email}")
            
            return redirect(url_for('bots.edit_bot', slug=slug))
            
        except Exception as e:
            logger.error(f"Erro ao atualizar bot: {e}")
            flash('Erro ao atualizar bot. Tente novamente.', 'error')
            db.session.rollback()
    
    return render_template('bots/edit.html', bot=bot)