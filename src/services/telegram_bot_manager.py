import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import urllib3

from ..services.offer_service import offer_service


# Desabilita warnings SSL temporariamente para resolver problema de conectividade
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from ..models.bot import TelegramBot
from ..models.payment import Payment
from ..models.client import User
from ..services.pushinpay_service import PushinPayService
from ..database.models import db
from ..utils.logger import logger
import json
import uuid

class TelegramBotManager:
    """Gerenciador de bots Telegram ativos"""
    
    def __init__(self):
        self.active_bots: Dict[str, Application] = {}  # bot_token -> Application
        self.pushinpay_service = PushinPayService()
    
    async def _check_network_connectivity(self) -> bool:
        """Verifica conectividade de rede com o Telegram"""
        import requests
        try:
            response = requests.get('https://api.telegram.org/', timeout=10)
            # 200 ou 401 são códigos OK para conectividade
            return response.status_code in [200, 401]
        except Exception as e:
            logger.warning(f"Falha na verificação de conectividade: {e}")
            return False
    
    async def start_bot(self, bot_config: TelegramBot) -> bool:
        """Inicia um bot Telegram individual"""
        max_retries = 5
        retry_delay = 10
        
        # Verifica conectividade antes de tentar (mas não falha se não conseguir)
        connectivity_ok = await self._check_network_connectivity()
        if not connectivity_ok:
            logger.warning("Problemas de conectividade detectados, mas tentando iniciar bot mesmo assim...")
        else:
            logger.info("Conectividade com Telegram API confirmada")
        
        for attempt in range(max_retries):
            try:
                if bot_config.bot_token in self.active_bots:
                    logger.info(f"Bot {bot_config.bot_username} já está rodando")
                    return True
                
                logger.info(f"Tentativa {attempt + 1}/{max_retries} de iniciar bot {bot_config.bot_username}")
                
                # Cria aplicação do bot com configurações padrão (Telegram requer SSL)
                application = Application.builder().token(bot_config.bot_token).build()
                
                # Adiciona handlers
                application.add_handler(CommandHandler("start", self._handle_start))
                application.add_handler(CallbackQueryHandler(self._handle_callback))
                
                # Handler para QUALQUER mensagem (teste)
                application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_start))
                
                # Armazena configuração do bot no contexto da aplicação
                application.bot_data['config'] = bot_config
                
                # Inicia o bot
                await application.initialize()
                await application.start()
                
                # Teste de conectividade antes do polling
                try:
                    me = await application.bot.get_me()
                    logger.info(f"✅ Bot conectado: @{me.username} - {me.first_name}")
                except Exception as e:
                    logger.error(f"❌ Erro ao conectar bot: {e}")
                    if attempt == max_retries - 1:
                        return False
                    continue
                
                # Inicia polling em modo não-bloqueante
                logger.info("🔄 Iniciando polling...")
                print("🔄 Iniciando polling...")
                
                # Testa se consegue receber updates primeiro
                try:
                    updates = await application.bot.get_updates(limit=1, timeout=1)
                    logger.info(f"✅ Teste de updates: {len(updates)} mensagens pendentes")
                    print(f"✅ Teste de updates: {len(updates)} mensagens pendentes")
                except Exception as update_error:
                    logger.error(f"❌ Erro ao testar updates: {update_error}")
                    print(f"❌ Erro ao testar updates: {update_error}")
                
                await application.updater.start_polling(
                    poll_interval=1.0,
                    timeout=20,
                    bootstrap_retries=3,
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                    drop_pending_updates=False  # Mudança: não descartar mensagens pendentes
                )
                
                logger.info(f"🔄 Polling iniciado para bot {bot_config.bot_username}")
                logger.info(f"🎯 Bot está aguardando mensagens. Teste enviando /start para @{me.username}")
                
                # Armazena na lista de bots ativos
                self.active_bots[bot_config.bot_token] = application
                
                # Atualiza status no banco
                bot_config.is_running = True
                db.session.commit()
                
                logger.info(f"Bot {bot_config.bot_username} iniciado com sucesso")
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Tentativa {attempt + 1} falhou para bot {bot_config.bot_username}: {e}")
                
                # Se é erro SSL, tenta aguardar mais tempo
                if "SSL" in error_msg or "TLS" in error_msg:
                    if attempt < max_retries - 1:
                        # Para problemas SSL, aguarda mais tempo
                        current_delay = retry_delay * (attempt + 2)  # Aumenta mais o delay
                        logger.info(f"Erro SSL detectado. Aguardando {current_delay}s antes da próxima tentativa...")
                        await asyncio.sleep(current_delay)
                elif attempt < max_retries - 1:
                    # Delay normal para outros erros
                    current_delay = retry_delay * (attempt + 1)
                    logger.info(f"Aguardando {current_delay}s antes da próxima tentativa...")
                    await asyncio.sleep(current_delay)
                else:
                    logger.error(f"Todas as tentativas falharam para bot {bot_config.bot_username}")
                    return False
    
    async def stop_bot(self, bot_token: str) -> bool:
        """Para um bot Telegram específico"""
        try:
            if bot_token not in self.active_bots:
                return True
            
            application = self.active_bots[bot_token]
            
            # Para o bot
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            
            # Remove da lista
            del self.active_bots[bot_token]
            
            # Atualiza status no banco
            bot_config = TelegramBot.query.filter_by(bot_token=bot_token).first()
            if bot_config:
                bot_config.is_running = False
                db.session.commit()
            
            logger.info(f"Bot parado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar bot: {e}")
            return False
    
    async def start_all_active_bots(self):
        """Inicia todos os bots ativos do banco de dados"""
        try:
            active_bots = TelegramBot.query.filter_by(is_active=True).all()
            
            for bot_config in active_bots:
                await self.start_bot(bot_config)
                
            logger.info(f"Iniciados {len(active_bots)} bots")
            
        except Exception as e:
            logger.error(f"Erro ao iniciar bots: {e}")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /start"""
        try:
            user = update.effective_user
            logger.info(f"🚀 Comando /start recebido de @{user.username or user.id}")
            
            # Verifica se a configuração do bot está disponível
            if 'config' not in context.application.bot_data:
                logger.error("❌ Configuração do bot não encontrada no contexto!")
                await update.message.reply_text("⚠️ Erro de configuração. Tente novamente.")
                return
            
            bot_config = context.application.bot_data['config']
            logger.info(f"Bot config encontrada: {bot_config.bot_username}")
            
            # Captura parâmetros UTM do comando /start se existirem
            start_params = context.args[0] if context.args else 'X'
            if start_params:
                try:
                    from ..models.codigo_venda import CodigoVenda
                    codigo_venda = CodigoVenda.create_from_start_params(
                        bot_id=bot_config.id,
                        telegram_user=user,
                        start_param=start_params
                    )
                    context.user_data['codigo_venda_id'] = codigo_venda.id
                    logger.info(f"✅ Código de venda criado com ID: {codigo_venda.id}")
                except Exception as utm_error:
                    logger.error(f"❌ Erro ao salvar código de venda: {utm_error}")
            
            # Mensagem de boas-vindas
            welcome_text = bot_config.welcome_message or "Olá! Bem-vindo ao meu bot!"
            
            # Cria botões com valores PIX e nomes dos planos
            try:
                pix_values = bot_config.get_pix_values()
                plan_names = bot_config.get_plan_names()
            except Exception as pix_error:
                logger.error(f"❌ Erro ao obter valores PIX: {pix_error}")
                pix_values = None
                plan_names = None
            
            keyboard = []
            
            if pix_values:
                # Cria botões para cada valor com nome do plano
                for i, value in enumerate(pix_values):
                    # Pega o nome do plano ou usa um padrão
                    plan_name = plan_names[i] if plan_names and i < len(plan_names) else f"Plano {i+1}"
                    
                    callback_data = f"pix_{value}_{bot_config.id}_{i}"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{plan_name} - R$ {value:.2f}",
                            callback_data=callback_data
                        )
                    ])
            else:
                # Valores padrão se não configurado
                default_values = [19.90, 39.90, 99.90]
                default_names = ["🌟VIP SEMANAL🌟", "💎PREMIUM MENSAL💎", "👑ELITE ANUAL👑"]
                
                for i, value in enumerate(default_values):
                    plan_name = default_names[i]
                    callback_data = f"pix_{value}_{bot_config.id}_{i}"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{plan_name} - R$ {value:.2f}",
                            callback_data=callback_data
                        )
                    ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # NOVA LÓGICA LIMPA PARA ENVIO DE MÍDIA
            logger.info(f"📷 Verificando mídia configurada para bot {bot_config.bot_username}")
            
            # STEP 1: Envia imagem/vídeo se existir
            await self._send_welcome_image(update, bot_config)
            
            # STEP 2: Envia áudio se existir  
            await self._send_welcome_audio(update, bot_config)
            
            # STEP 3: Envia mensagem de boas-vindas com botões
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup
            )
            
            logger.info(f"✅ Resposta enviada com sucesso para @{user.username or user.id} no bot {bot_config.bot_username}")
            
        except Exception as e:
            logger.error(f"❌ Erro no handler /start: {e}")
            try:
                await update.message.reply_text("Desculpe, ocorreu um erro. Tente novamente.")
            except:
                pass

    async def _send_welcome_image(self, update: Update, bot_config):
        """Envia imagem/vídeo de boas-vindas se configurada"""
        try:
            # Verifica se tem imagem via file_id (prioridade)
            if hasattr(bot_config, 'welcome_image_file_id') and bot_config.welcome_image_file_id:
                logger.info(f"🖼️ Enviando imagem via file_id: {bot_config.welcome_image_file_id}")
                
                for attempt in range(2):
                    try:
                        await update.message.reply_photo(
                            photo=bot_config.welcome_image_file_id,
                            read_timeout=30,
                            write_timeout=30,
                            connect_timeout=30
                        )
                        logger.info(f"✅ Imagem enviada com sucesso via file_id")
                        return True
                    except Exception as img_error:
                        logger.warning(f"⚠️ Tentativa {attempt + 1} falhou ao enviar imagem: {img_error}")
                        if attempt < 1:
                            await asyncio.sleep(2)
            
            # Verifica se tem vídeo via file_id
            elif hasattr(bot_config, 'welcome_video_file_id') and bot_config.welcome_video_file_id:
                logger.info(f"🎥 Enviando vídeo via file_id: {bot_config.welcome_video_file_id}")
                
                for attempt in range(2):
                    try:
                        await update.message.reply_video(
                            video=bot_config.welcome_video_file_id,
                            read_timeout=45,
                            write_timeout=45,
                            connect_timeout=30
                        )
                        logger.info(f"✅ Vídeo enviado com sucesso via file_id")
                        return True
                    except Exception as vid_error:
                        logger.warning(f"⚠️ Tentativa {attempt + 1} falhou ao enviar vídeo: {vid_error}")
                        if attempt < 1:
                            await asyncio.sleep(2)
            
            # Fallback para arquivo local (sistema legado)
            elif hasattr(bot_config, 'welcome_image') and bot_config.welcome_image:
                try:
                    import os
                    if os.path.exists(bot_config.welcome_image):
                        logger.info(f"🖼️ Enviando imagem via arquivo local: {bot_config.welcome_image}")
                        
                        file_extension = os.path.splitext(bot_config.welcome_image)[1].lower()
                        
                        if file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                            with open(bot_config.welcome_image, 'rb') as video_file:
                                await update.message.reply_video(
                                    video=video_file,
                                    read_timeout=60,
                                    write_timeout=60,
                                    connect_timeout=30
                                )
                            logger.info(f"✅ Vídeo enviado via arquivo local")
                        else:
                            with open(bot_config.welcome_image, 'rb') as img_file:
                                await update.message.reply_photo(
                                    photo=img_file,
                                    read_timeout=30,
                                    write_timeout=30,
                                    connect_timeout=30
                                )
                            logger.info(f"✅ Imagem enviada via arquivo local")
                        return True
                    else:
                        logger.warning(f"⚠️ Arquivo de imagem não encontrado: {bot_config.welcome_image}")
                except Exception as local_error:
                    logger.error(f"❌ Erro ao enviar mídia local: {local_error}")
            
            # Sem mídia configurada
            else:
                logger.info("📷 Nenhuma imagem/vídeo configurada")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro geral ao enviar imagem: {e}")
            return False

    async def _send_welcome_audio(self, update: Update, bot_config):
        """Envia áudio de boas-vindas se configurado"""
        try:
            # Verifica se tem áudio via file_id (prioridade)
            if hasattr(bot_config, 'welcome_audio_file_id') and bot_config.welcome_audio_file_id:
                logger.info(f"🎵 Enviando áudio via file_id: {bot_config.welcome_audio_file_id}")
                
                for attempt in range(2):
                    try:
                        # Para OGG, sempre usar como voice message
                        await update.message.reply_voice(
                            voice=bot_config.welcome_audio_file_id,
                            read_timeout=45,
                            write_timeout=45,
                            connect_timeout=30
                        )
                        logger.info(f"✅ Áudio enviado com sucesso via file_id como voice message")
                        return True
                    except Exception as audio_error:
                        logger.warning(f"⚠️ Tentativa {attempt + 1} falhou ao enviar áudio: {audio_error}")
                        
                        # Se falhar como voice, tenta como audio
                        if attempt == 0:
                            try:
                                await update.message.reply_audio(
                                    audio=bot_config.welcome_audio_file_id,
                                    read_timeout=45,
                                    write_timeout=45,
                                    connect_timeout=30
                                )
                                logger.info(f"✅ Áudio enviado com sucesso via file_id como audio")
                                return True
                            except Exception as audio_error2:
                                logger.warning(f"⚠️ Também falhou como audio: {audio_error2}")
                        
                        if attempt < 1:
                            await asyncio.sleep(2)
            
            # Fallback para arquivo local (sistema legado)
            elif hasattr(bot_config, 'welcome_audio') and bot_config.welcome_audio:
                try:
                    import os
                    if os.path.exists(bot_config.welcome_audio):
                        logger.info(f"🎵 Enviando áudio via arquivo local: {bot_config.welcome_audio}")
                        
                        file_size = os.path.getsize(bot_config.welcome_audio)
                        max_size = 25 * 1024 * 1024  # 25MB
                        
                        if file_size > max_size:
                            logger.error(f"❌ Áudio muito grande: {file_size/1024/1024:.1f}MB")
                        else:
                            with open(bot_config.welcome_audio, 'rb') as audio_file:
                                await update.message.reply_voice(
                                    voice=audio_file,
                                    read_timeout=45,
                                    write_timeout=45,
                                    connect_timeout=30
                                )
                            logger.info(f"✅ Áudio enviado via arquivo local")
                            return True
                    else:
                        logger.warning(f"⚠️ Arquivo de áudio não encontrado: {bot_config.welcome_audio}")
                except Exception as local_audio_error:
                    logger.error(f"❌ Erro ao enviar áudio local: {local_audio_error}")
            
            # Sem áudio configurado
            else:
                logger.info("🎵 Nenhum áudio configurado")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro geral ao enviar áudio: {e}")
            return False

    def _detect_media_type(self, file_id: str) -> str:
        """Detecta tipo de mídia pelo file_id"""
        if not file_id:
            return 'unknown'
        
        # File IDs do Telegram têm padrões específicos
        if file_id.startswith('AgAC') or file_id.startswith('AAMC'):
            return 'photo'
        elif file_id.startswith('BAACAgIAAxkBAAM') or file_id.startswith('BAACAgEAAxkBAAM'):
            return 'video'
        elif file_id.startswith('AwACAgIAAxkBAAM') or file_id.startswith('AwACAgEAAxkBAAM'):
            return 'audio'
        else:
            return 'photo'  # Default para foto

    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para botões inline (valores PIX e verificação de pagamento)"""
        try:
            query = update.callback_query
            await query.answer()
            
            callback_data = query.data
            
            # Verifica se é um callback de verificação de pagamento
            if callback_data.startswith('check_'):
                await self._handle_payment_verification(update, context)
                return
            
            # Verifica se é callback para voltar ao início
            if callback_data == 'start':
                await self._handle_start_callback(update, context)
                return
            
            if callback_data.startswith('order_bump_accept_'):
                await self._handle_order_bump_accept(update, context)
                return
            if callback_data.startswith('order_bump_decline_'):
                await self._handle_order_bump_decline(update, context)
                return

            # Parse do callback data: "pix_19.90_1_0" (valor_bot_id_plan_index)
            callback_parts = callback_data.split('_')
            if len(callback_parts) < 3 or callback_parts[0] != 'pix':
                await query.edit_message_text("Erro: Dados inválidos")
                return

            value = float(callback_parts[1])
            bot_id = int(callback_parts[2])
            plan_index = int(callback_parts[3]) if len(callback_parts) > 3 else 0
            
            # Busca configuração do bot
            bot_config = TelegramBot.query.get(bot_id)
            if not bot_config:
                await query.edit_message_text("Erro: Bot não encontrado")
                return

            order_bump = offer_service.get_active_order_bump(bot_id)
            
            if (order_bump):
                telegram_user_id = update.effective_user.id

                already_accepted = offer_service.has_accepted_offer(
                    telegram_user_id,
                    order_bump.id
                )

                context.user_data['pending_main_payment'] = {
                    'value': value,
                    'bot_id': bot_id,
                    'plan_index': plan_index
                }

                # Mostra Order Bump (sem editar mensagem original)
                await self._show_order_bump(update, context, order_bump, bot_config)
                return
            
            # Envia mensagem de loading antes de gerar PIX
            loading_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⏳ Aguarde um momento, estamos gerando seu pagamento..."
            )
            
            # Armazena ID da mensagem de loading
            context.user_data['loading_message_id'] = loading_message.message_id
            
            # Gera PIX normal
            await self._generate_pix_payment(
                update, context, bot_config, value, plan_index
            )
            
        except Exception as e:
            logger.error(f"Erro no handler callback: {e}")
            await query.edit_message_text("❌ Erro ao processar solicitação. Tente novamente.")
    
    
    async def _handle_start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para callback 'start' - volta ao menu inicial"""
        try:
            # Simula um comando /start
            await self._handle_start(update, context)
        except Exception as e:
            logger.error(f"Erro no handler start callback: {e}")
    
    
    async def _handle_payment_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para verificação de pagamento PIX"""
        try:
            query = update.callback_query
            user = update.effective_user
            
            logger.info(f"🔍 Iniciando verificação de pagamento para @{user.username or user.id}")
            
            # Extrai o ID do pagamento do callback data
            payment_id = int(query.data.split('_')[1])
            logger.info(f"📋 ID do pagamento a verificar: {payment_id}")
            
            # Busca o pagamento no banco
            payment = Payment.query.get(payment_id)
            if not payment:
                await query.edit_message_text("❌ Pagamento não encontrado.")
                return
            
            # Busca a configuração do bot
            bot_config = TelegramBot.query.get(payment.bot_id)
            if not bot_config:
                await query.edit_message_text("❌ Configuração do bot não encontrada.")
                return
            
            # Busca o dono do bot
            bot_owner = User.query.get(bot_config.user_id)
            if not bot_owner or not bot_owner.pushinpay_token:
                await query.edit_message_text("❌ Sistema de pagamento indisponível. Tente novamente mais tarde")
                return
            


            
            # Verifica com a API do PushinPay
            try:
                pushin_service = PushinPayService()

                transaction_id = payment.pix_code
                
                # Usa o pix_code como payment_id para verificar o status
                payment_status = pushin_service.check_payment_status(
                    bot_owner.pushinpay_token, 
                    transaction_id
                )
                payment_verified = payment_status.get('paid', False)
                
                logger.info(f"📊 Status do pagamento {transaction_id}: {payment_status}")
                
            except Exception as api_error:
                logger.error(f"❌ Erro ao verificar pagamento via API: {api_error}")
                # Em caso de erro na API, considera como não pago
                payment_verified = False
            
            if payment_verified:
                # Pagamento aprovado! 
                payment.status = 'approved' or 'completed'
                payment.paid_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"✅ Pagamento aprovado! Adicionando @{user.username or user.id} aos grupos")
                
                # Adiciona o usuário ao grupo VIP
                success_vip = await self._add_user_to_group(
                    context.bot, 
                    user.id, 
                    bot_config.get_vip_group_id(),
                    "VIP"
                )
                
                # Pega informações do plano
                plan_names = bot_config.get_plan_names()
                plan_durations = bot_config.get_plan_durations()
                plan_name = "Plano Não Identificado"
                plan_duration = "indefinido"
                
                # Tenta encontrar o plano baseado no valor
                pix_values = bot_config.get_pix_values()
                if pix_values:
                    for i, value in enumerate(pix_values):
                        if abs(value - payment.amount) < 0.01:  # Comparação com tolerância
                            if plan_names and i < len(plan_names):
                                plan_name = plan_names[i]
                            if plan_durations and i < len(plan_durations):
                                plan_duration = plan_durations[i]
                            break
                
                # Envia notificação para o grupo de logs
                try:
                    logger.info(f"📝 Tentando enviar notificação para grupo de logs...")
                    await self._send_log_notification(
                        context.bot,
                        bot_config.get_log_group_id(),
                        user,
                        payment.amount,
                        success_vip,
                        payment,
                        bot_config,
                        plan_name,
                        plan_duration
                    )
                    logger.info(f"✅ Notificação enviada com sucesso!")
                except Exception as log_error:
                    logger.error(f"❌ Erro ao enviar notificação de log: {log_error}")
                    # Continua mesmo se falhar o log
                
                # Resposta ao usuário
                if success_vip:
                    success_message = f"""✅ PAGAMENTO APROVADO!

🎉 Parabéns! Seu pagamento foi confirmado.
👑 Você foi adicionado ao grupo VIP!

Aproveite o acesso exclusivo! 🚀"""
                else:
                    success_message = f"""✅ **PAGAMENTO APROVADO!**

🎉 Parabéns! Seu pagamento foi confirmado.

⚠️ Houve um problema ao adicionar você ao grupo automaticamente.
Entre em contato com o suporte."""
                
                # Responde ao callback
                await query.answer("Pagamento aprovado!")
                
                # Envia nova mensagem de sucesso
                await context.bot.send_message(
                    chat_id=user.id,
                    text=success_message,
                )
                
            else:
                # Pagamento ainda pendente
                await query.answer("Pagamento ainda pendente...")
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Verificar Novamente", callback_data=f"check_{payment_id}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "⏳ Pagamento ainda não foi identificado.\n\n"
                    "Aguarde alguns minutos após realizar o pagamento e tente novamente.",
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"❌ Erro na verificação de pagamento: {e}")
            await query.edit_message_text("❌ Erro ao verificar pagamento. Tente novamente.")
    
    async def _add_user_to_group(self, bot, user_id: int, group_id: str, group_type: str) -> bool:
        """Adiciona usuário a um grupo específico"""
        try:
            if not group_id:
                logger.warning(f"⚠️  ID do grupo {group_type} não configurado")
                return False
            
            logger.info(f"➕ Tentando adicionar usuário {user_id} ao grupo {group_type} ({group_id})")
            
            # Gera link de convite para o grupo
            invite_link = await bot.create_chat_invite_link(
                chat_id=group_id,
                member_limit=1,  # Link para apenas 1 pessoa
                expire_date=None  # Link temporário
            )
            
            # Envia o link por mensagem privada
            await bot.send_message(
                chat_id=user_id,
                text=f"🎊 **ACESSO LIBERADO!**\n\n"
                     f"👑 Clique no link abaixo para entrar no grupo VIP:\n\n"
                     f"{invite_link.invite_link}\n\n"
                     f"🚀 Aproveite o conteúdo exclusivo!"
            )
            
            logger.info(f"✅ Link de convite enviado para usuário {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar usuário {user_id} ao grupo {group_type}: {e}")
            return False
    
    async def _send_log_notification(self, bot, log_group_id: str, user, amount: float, success: bool, payment=None, bot_config=None, plan_name="", plan_duration=""):
        """Envia notificação melhorada para o grupo de logs"""
        try:
            if not log_group_id:
                logger.warning("⚠️  ID do grupo de logs não configurado")
                return
            
            # Busca informações extras do usuário do Telegram
            user_info = await self._get_enhanced_user_info(user, payment, bot_config)
            
            # Calcula valor líquido (deduz R$1.00 conforme especificação)
            net_value = amount - 1.00
            
            # Busca informações do código de venda para tempo de conversão e código
            codigo_venda_info = self._get_codigo_venda_info(payment)
            conversion_time = codigo_venda_info.get('conversion_time', '0d 0h 2m 37s')
            sale_code = codigo_venda_info.get('sale_code', 'CodigoGeradoNoStartViaUrL')
            
            # Determina categoria do plano
            plan_category = self._get_plan_category(plan_name)
            
            # Monta a notificação com informações corretas do usuário do Telegram
            # user = usuário do Telegram que usou o bot (NÃO é o dono do bot)
            telegram_full_name = f"{user.first_name} {user.last_name or ''}".strip()
            
            log_message = f"""🎉 Pagamento Aprovado!
🤖 Bot: @{bot_config.bot_username if bot_config else 'bot_desconhecido'}
⚙️ ID Bot: {bot_config.id if bot_config else 'N/A'}
🆔 ID Cliente: {user.id}
🔗 Username: @{user.username or 'sem_username'}
👤 Nome de Perfil: {telegram_full_name}
👤 Nome Completo: {user_info.get('full_name', telegram_full_name)}
💳 CPF: {user_info.get('cpf_masked', 'N/A')}
📦 Categoria: {plan_category}
🎁 Plano: {plan_name} 💎
📅 Duração: {plan_duration.title() if plan_duration else 'N/A'}
💰 Valor: R${amount:.2f}
💵 Valor Líquido: R${net_value:.2f}
⏳ Tempo Conversão: {conversion_time}
🔖 Código de Venda: {sale_code}
🏷️ ID Gateway: {user_info.get('gateway_id', payment.pix_code if payment else 'N/A')}
💱 Moeda: BRL
💳 Método: PIX
🏦 Plataforma: PushinPay"""
            
            await bot.send_message(
                chat_id=log_group_id,
                text=log_message
            )
            
            logger.info(f"📝 Notificação melhorada enviada para grupo de logs")
            
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação para logs: {e}")
    
    def _get_plan_category(self, plan_name: str) -> str:
        """Determina a categoria do plano baseado no nome"""
        plan_name_lower = plan_name.lower()
        
        if 'downsell' in plan_name_lower or 'desconto' in plan_name_lower:
            return "Plano Downsell"
        elif 'upsell' in plan_name_lower or 'premium' in plan_name_lower or 'vip' in plan_name_lower:
            return "Plano Premium"
        elif 'mailing' in plan_name_lower or 'email' in plan_name_lower:
            return "Plano Mailing"
        elif 'pacote' in plan_name_lower or 'bundle' in plan_name_lower:
            return "Plano Pacotes"
        else:
            return "Plano Normal"
    
    async def _get_enhanced_user_info(self, telegram_user, payment=None, bot_config=None) -> dict:
        """Busca informações aprimoradas do usuário do Telegram"""
        try:            
            # Monta nome completo do usuário do Telegram
            telegram_full_name = f"{telegram_user.first_name} {telegram_user.last_name or ''}".strip()
            
            # Se temos um pagamento, verifica se já temos dados do pagador real
            if payment:
                # Dados reais do pagador (vindos da PushinPay via webhook)
                try:
                    real_name = getattr(payment, 'payer_name', None) or telegram_full_name
                    real_cpf = self._mask_cpf(getattr(payment, 'payer_cpf', None)) if getattr(payment, 'payer_cpf', None) else 'N/A'
                except Exception as attr_error:
                    logger.error(f"Erro ao acessar atributos do payment: {attr_error}")
                    real_name = telegram_full_name
                    real_cpf = 'N/A'
            else:
                real_name = telegram_full_name
                real_cpf = 'N/A'
            
            return {
                'full_name': real_name,
                'cpf_masked': real_cpf,
                'gateway_id': payment.pix_code if payment else 'N/A',
                'is_premium': getattr(telegram_user, 'is_premium', False),
                'language_code': getattr(telegram_user, 'language_code', 'pt-br')
            }
        except Exception as e:
            logger.error(f"Erro ao buscar info aprimorada do usuário {telegram_user.id}: {e}")
            return {
                'full_name': f"{telegram_user.first_name} {telegram_user.last_name or ''}".strip(),
                'cpf_masked': 'N/A',
                'gateway_id': 'N/A',
                'is_premium': False,
                'language_code': 'pt-br'
            }

    async def _get_pushinpay_user_data(self, payment, bot_config) -> dict:
        """Busca dados do usuário na API da PushinPay"""
        try:
            # Busca o dono do bot para pegar o token PushinPay
            from ..models.client import User
            bot_owner = User.query.get(bot_config.user_id)
            
            if not bot_owner or not bot_owner.pushinpay_token:
                return {}
            
            # Tenta buscar informações da transação na PushinPay
            pushin_service = PushinPayService()
            payment_details = pushin_service.check_payment_status(
                bot_owner.pushinpay_token,
                payment.pix_code
            )
            
            if payment_details.get('success') and payment_details.get('data'):
                data = payment_details['data']
                
                # Extrai informações do pagador se disponíveis
                payer_info = data.get('payer', {})
                
                return {
                    'full_name': payer_info.get('name', ''),
                    'cpf_masked': self._mask_cpf(payer_info.get('cpf', '')),
                    'gateway_id': data.get('gateway_id', payment.pix_code)
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao buscar dados PushinPay: {e}")
            return {}
        


    async def _show_order_bump(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                               order_bump, bot_config: TelegramBot):
        """Mostra oferta de Order Bump"""
        query = update.callback_query
        logger.info('entrou no show order bump')
        
        # Envia mídias em novas mensagens (não edita a original)
        if order_bump.media_image_file_id:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=order_bump.media_image_file_id
            )
        
        if order_bump.media_video_file_id:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=order_bump.media_video_file_id
            )
        
        if order_bump.media_audio_file_id:
            await update.message.reply_voice(
                voice=order_bump.media_audio_file_id,
                read_timeout=45,
                write_timeout=45,
                connect_timeout=30
            )
        
        # Mensagem do order bump
        message = f"{order_bump.message}\n\n💰 Valor: R$ {order_bump.order_bump_config.price:.2f}"
        
        # Botões
        keyboard = [
            [InlineKeyboardButton(
                order_bump.accept_button_text,
                callback_data=f"order_bump_accept_{order_bump.id}"
            )],
            [InlineKeyboardButton(
                order_bump.decline_button_text,
                callback_data=f"order_bump_decline_{order_bump.id}"
            )]
        ]
        
        # Envia em nova mensagem (não edita a original)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        logger.info(f"🎁 Order Bump exibido: {order_bump.name}")
    
    async def _handle_order_bump_accept(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler quando aceita order bump"""
        query = update.callback_query
        offer_id = int(query.data.split('_')[3])
        
        main_payment = context.user_data.get('pending_main_payment')
        if not main_payment:
            await query.edit_message_text("❌ Sessão expirada.")
            return
        
        order_bump = offer_service.get_active_order_bump(main_payment['bot_id'])
        if not order_bump:
            await query.edit_message_text("❌ Oferta não encontrada.")
            return
        
        # Soma valores
        total_amount = main_payment['value'] + float(order_bump.order_bump_config.price)
        
        await query.answer("✅ Oferta aceita!")
        
        # Envia mensagem de loading em nova mensagem
        loading_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏳ Aguarde um momento, estamos gerando seu pagamento..."
        )
        
        # Armazena ID da mensagem de loading
        context.user_data['loading_message_id'] = loading_message.message_id
        
        bot_config = TelegramBot.query.get(main_payment['bot_id'])
        
        await self._generate_pix_payment(
            update, context, bot_config, total_amount, main_payment['plan_index'],
            offer_id=offer_id,
            offer_amount=float(order_bump.order_bump_config.price)
        )
    
    async def _handle_order_bump_decline(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler quando recusa order bump"""
        query = update.callback_query
        main_payment = context.user_data.get('pending_main_payment')
        
        if not main_payment:
            await query.edit_message_text("❌ Sessão expirada.")
            return
        
        await query.answer("Ok!")
        
        # Envia mensagem de loading em nova mensagem
        loading_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⏳ Aguarde um momento, estamos gerando seu pagamento..."
        )
        
        # Armazena ID da mensagem de loading
        context.user_data['loading_message_id'] = loading_message.message_id
        
        bot_config = TelegramBot.query.get(main_payment['bot_id'])
        
        await self._generate_pix_payment(
            update, context, bot_config, 
            main_payment['value'], main_payment['plan_index']
        )

    async def _generate_pix_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                    bot_config: TelegramBot, amount: float, plan_index: int,
                                    offer_id: int = None, offer_amount: float = None):
        """Função centralizada para gerar pagamento PIX"""
        try:
            user = update.effective_user
            
            # Busca o dono do bot para pegar o token PushinPay
            bot_owner = User.query.get(bot_config.user_id)
            if not bot_owner or not bot_owner.pushinpay_token:
                await self._send_error_message(update, "Erro: Sistema de pagamento indisponível")
                return
            
            # Pega informações do plano
            plan_info = self._get_plan_info(bot_config, plan_index, amount)
            
            # Cria descrição do pagamento
            description = f"Pagamento R$ {amount:.2f} - Bot {bot_config.bot_username}"
            if offer_id:
                description += " (com Order Bump)"
            
            # Gera PIX via PushinPay
            pix_data = self.pushinpay_service.create_pix_payment(
                user_pushinpay_token=bot_owner.pushinpay_token,
                amount=amount,
                telegram_user_id=str(user.id),
                description=description
            )
            
            if not pix_data.get('success'):
                await self._send_error_message(
                    update,
                    f"❌ Erro ao gerar PIX: {pix_data.get('error', 'Erro desconhecido')}"
                )
                return
            
            # Salva pagamento no banco
            payment = self._create_payment_record(
                pix_data, amount, bot_config, user
            )
            
            # Registra order bump se aplicável
            if offer_id and offer_amount:
                self._register_order_bump(offer_id, payment.id, offer_amount)
            
            # Conecta código de venda
            self._connect_codigo_venda(context, payment.id)
            
            # Envia PIX para o usuário
            await self._send_pix_to_user(
                update, context, pix_data, amount, 
                plan_info, payment.id, offer_id is not None
            )
            
            logger.info(f"✅ PIX gerado: R$ {amount:.2f} para @{user.username or user.id}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar PIX: {e}")
            await self._send_error_message(update, "❌ Erro ao gerar pagamento. Tente novamente.")

    def _get_plan_info(self, bot_config: TelegramBot, plan_index: int, amount: float) -> dict:
        """Obtém informações do plano"""
        plan_names = bot_config.get_plan_names()
        plan_durations = bot_config.get_plan_durations()
        
        # Nomes padrão
        default_names = ["🌟VIP SEMANAL🌟", "💎PREMIUM MENSAL💎", "👑ELITE ANUAL👑"]
        default_durations = ["Semanal", "Mensal", "Anual"]
        
        plan_name = "Plano Especial"
        plan_duration = "Mensal"
        
        # Tenta pegar nome do plano configurado
        if plan_names and plan_index < len(plan_names):
            plan_name = plan_names[plan_index]
        elif plan_index < len(default_names):
            plan_name = default_names[plan_index]
        
        # Tenta pegar duração do plano configurado
        if plan_durations and plan_index < len(plan_durations):
            plan_duration = plan_durations[plan_index].title()
        elif plan_index < len(default_durations):
            plan_duration = default_durations[plan_index]
        
        return {
            'name': plan_name,
            'duration': plan_duration,
            'amount': amount
        }

    def _create_payment_record(self, pix_data: dict, amount: float, 
                               bot_config: TelegramBot, user) -> Payment:
        """Cria registro de pagamento no banco"""
        payment = Payment(
            pix_code=pix_data['pix_code'],
            amount=amount,
            pix_key=pix_data.get('pix_copy_paste', ''),
            pix_qr_code=pix_data.get('qr_code', ''),
            expires_at=pix_data.get('expires_at'),
            user_id=bot_config.user_id,
            bot_id=bot_config.id,
            telegram_user_id=user.id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
            telegram_last_name=user.last_name
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return payment

    def _register_order_bump(self, offer_id: int, payment_id: int, offer_amount: float):
        """Registra order bump aceito"""
        try:
            offer_service.record_offer_payment(
                offer_id=offer_id,
                payment_id=payment_id,
                offer_amount=offer_amount
            )
            logger.info(f"✅ Order Bump registrado: payment_id={payment_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao registrar order bump: {e}")

    def _connect_codigo_venda(self, context: ContextTypes.DEFAULT_TYPE, payment_id: int):
        """Conecta código de venda ao pagamento"""
        codigo_venda_id = context.user_data.get('codigo_venda_id')
        if codigo_venda_id:
            try:
                from ..models.codigo_venda import CodigoVenda
                codigo_venda = CodigoVenda.query.get(codigo_venda_id)
                if codigo_venda:
                    codigo_venda.mark_as_used(payment_id)
                    logger.info(f"✅ Código de venda {codigo_venda_id} conectado ao pagamento {payment_id}")
            except Exception as cv_error:
                logger.error(f"❌ Erro ao conectar código de venda: {cv_error}")

    async def _send_pix_to_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                pix_data: dict, amount: float, plan_info: dict, 
                                payment_id: int, has_order_bump: bool = False):
        """Envia dados do PIX para o usuário"""
        user = update.effective_user
        
        # Cria botões
        keyboard = [
            [InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"check_{payment_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Pega o código PIX completo (sem truncar)
        pix_copy_paste = pix_data.get('pix_copy_paste', 'PIX não disponível')
        
        # Mensagem PIX
        order_bump_text = " + Order Bump" if has_order_bump else ""
        pix_message = f"""🌟 Você selecionou o seguinte plano:

🎁 Plano: {plan_info['name']}{order_bump_text}
📅 Duração: {plan_info['duration']}
💰 Valor: R${amount:.2f}

💠 Pague via Pix Copia e Cola (ou QR Code em alguns bancos):

`{pix_copy_paste}`

👆 Toque na chave PIX acima para copiá-la

‼️ Após o pagamento, clique no botão abaixo para verificar o status:"""
        
        # Recupera ID da mensagem de loading
        loading_message_id = context.user_data.get('loading_message_id')
        
        # Tenta enviar com QR Code
        qr_code_data = pix_data.get('qr_code', '')
        if qr_code_data and qr_code_data.startswith('data:image/'):
            qr_sent = await self._send_qr_code(
                context, user.id, qr_code_data, pix_message, reply_markup,
                loading_message_id
            )
            if qr_sent:
                return
        
        # Fallback: edita mensagem de loading com o texto do PIX
        if loading_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=user.id,
                    message_id=loading_message_id,
                    text=pix_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Erro ao editar mensagem de loading: {e}")
                # Se falhar ao editar, envia nova mensagem
                await context.bot.send_message(
                    chat_id=user.id,
                    text=pix_message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            # Se não tem loading_message_id, envia nova mensagem
            await context.bot.send_message(
                chat_id=user.id,
                text=pix_message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def _send_qr_code(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int,
                           qr_code_data: str, caption: str, reply_markup,
                           loading_message_id: int = None) -> bool:
        """Envia QR Code como imagem"""
        # Se tem loading_message_id, deleta a mensagem de loading primeiro
        if loading_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=chat_id,
                    message_id=loading_message_id
                )
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível deletar mensagem de loading: {e}")
        
        for attempt in range(2):
            try:
                import base64
                from io import BytesIO
                from PIL import Image, ImageOps
                
                base64_data = qr_code_data.split(',')[1] if ',' in qr_code_data else qr_code_data
                image_data = base64.b64decode(base64_data)
                
                original_image = Image.open(BytesIO(image_data))
                padding = 20
                padded_image = ImageOps.expand(original_image, border=padding, fill='white')
                
                output_buffer = BytesIO()
                padded_image.save(output_buffer, format='PNG')
                output_buffer.seek(0)
                
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=output_buffer,
                    caption=caption,
                    reply_markup=reply_markup,
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                    parse_mode='Markdown'
                )
                
                logger.info(f"✅ QR Code enviado com sucesso na tentativa {attempt + 1}")
                return True
                
            except Exception as img_error:
                logger.warning(f"⚠️ Tentativa {attempt + 1} falhou ao enviar QR Code: {img_error}")
                if attempt < 1:
                    await asyncio.sleep(2)
        
        logger.error(f"❌ Falha ao enviar QR Code após 2 tentativas")
        return False

    async def _send_error_message(self, update: Update, message: str):
        """Envia mensagem de erro"""
        try:
            query = update.callback_query
            if query:
                await query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem de erro: {e}")
    
    def _mask_cpf(self, cpf: str) -> str:
        """Mascara CPF para exibição nos logs"""
        if not cpf or len(cpf) < 11:
            return 'N/A'
        
        # Remove caracteres não numéricos
        cpf_numbers = ''.join(filter(str.isdigit, cpf))
        
        if len(cpf_numbers) != 11:
            return 'N/A'
        
        # Formato: 123.***.**1-45
        return f"{cpf_numbers[:3]}.***.**{cpf_numbers[-3:]}"

    def _get_codigo_venda_info(self, payment) -> dict:
        """Busca informações do código de venda associado ao pagamento"""
        try:
            if not payment:
                return {
                    'conversion_time': '0d 0h 0m 0s',
                    'sale_code': 'CodigoGeradoNoStartViaUrL'
                }
            
            # Busca código de venda associado ao pagamento
            from ..models.codigo_venda import CodigoVenda
            codigo_venda = CodigoVenda.query.filter_by(payment_id=payment.id).first()
            
            if codigo_venda:
                # Calcula tempo de conversão
                if codigo_venda.created_at and payment.paid_at:
                    time_diff = payment.paid_at - codigo_venda.created_at
                    days = time_diff.days
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    conversion_time = f"{days}d {hours}h {minutes}m {seconds}s"
                else:
                    conversion_time = "0d 0h 0m 0s"
                

                sale_code = codigo_venda.unique_click_id
                
                return {
                    'conversion_time': conversion_time,
                    'sale_code': sale_code
                }
            
            return {
                'conversion_time': '0d 0h 0m 0s',
                'sale_code': 'CodigoGeradoNoStartViaUrL'
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar código de venda: {e}")
            return {
                'conversion_time': '0d 0h 0m 0s',
                'sale_code': 'CodigoGeradoNoStartViaUrL'
            }
    
    async def _get_user_info(self, bot, user_id: int) -> dict:
        """Busca informações do usuário no Telegram"""
        try:
            user = await bot.get_chat_member(user_id, user_id)
            return {
                'username': user.user.username,
                'first_name': user.user.first_name,
                'last_name': user.user.last_name
            }
        except Exception as e:
            logger.error(f"Erro ao buscar info do usuário {user_id}: {e}")
            return {'username': None, 'first_name': 'Usuário', 'last_name': ''}

# Instância global do gerenciador
bot_manager = TelegramBotManager()