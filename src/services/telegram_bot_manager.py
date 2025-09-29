import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import urllib3

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
                application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_any_text))
                
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
            print(f"🚀 Comando /start recebido de @{user.username or user.id}")
            
            # Verifica se a configuração do bot está disponível
            if 'config' not in context.application.bot_data:
                logger.error("❌ Configuração do bot não encontrada no contexto!")
                print("❌ Configuração do bot não encontrada no contexto!")
                await update.message.reply_text("⚠️ Erro de configuração. Tente novamente.")
                return
            
            bot_config = context.application.bot_data['config']
            
            logger.info(f"Bot config encontrada: {bot_config.bot_username}")
            print(f"Bot config encontrada: {bot_config.bot_username}")
            
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
            
            # Envia mídias iniciais na sequência correta APENAS se ambos os grupos estiverem configurados
            can_send_media = bot_config.has_vip_group() and bot_config.has_log_group()
            
            if can_send_media:
                # 1. Primeiro envia a imagem inicial se existir (via file_id ou caminho local)
                image_sent = False
                
                # Tenta enviar via file_id com retry
                if bot_config.welcome_image_file_id and not image_sent:
                    for retry_attempt in range(3):
                        try:
                            await update.message.reply_photo(photo=bot_config.welcome_image_file_id)
                            logger.info(f"✅ Imagem inicial enviada via file_id")
                            image_sent = True
                            break
                        except Exception as img_error:
                            if "SSL" in str(img_error) or "TLS" in str(img_error):
                                logger.warning(f"⚠️ Tentativa {retry_attempt + 1} falhou (SSL): {img_error}")
                                if retry_attempt < 2:
                                    await asyncio.sleep(2 * (retry_attempt + 1))  # 2s, 4s
                                    continue
                                else:
                                    logger.error(f"❌ Todas as tentativas de envio via file_id falharam")
                            else:
                                logger.error(f"❌ Erro ao enviar imagem via file_id: {img_error}")
                                break
                
                # Fallback para arquivo local se file_id falhou
                if not image_sent and bot_config.welcome_image:
                    try:
                        with open(bot_config.welcome_image, 'rb') as img_file:
                            await update.message.reply_photo(photo=img_file)
                        logger.info(f"✅ Imagem inicial enviada via arquivo local")
                        image_sent = True
                    except Exception as local_img_error:
                        logger.error(f"❌ Erro ao enviar imagem local: {local_img_error}")
                
                # Se nem file_id nem arquivo local, mas tem só arquivo local configurado
                if not image_sent and bot_config.welcome_image and not bot_config.welcome_image_file_id:
                    try:
                        with open(bot_config.welcome_image, 'rb') as img_file:
                            await update.message.reply_photo(photo=img_file)
                        logger.info(f"✅ Imagem inicial enviada via arquivo local")
                        image_sent = True
                    except Exception as local_img_error:
                        logger.error(f"❌ Erro ao enviar imagem local: {local_img_error}")
                
                # Log final sobre o status da imagem
                if not image_sent:
                    logger.warning(f"⚠️ Não foi possível enviar imagem inicial devido a problemas de conectividade. Continuando com o texto...")
                
                # 2. Depois envia o áudio inicial se existir (via file_id ou caminho local)
                audio_sent = False
                
                # Tenta enviar áudio via file_id com retry
                if bot_config.welcome_audio_file_id and not audio_sent:
                    for retry_attempt in range(3):
                        try:
                            await update.message.reply_audio(audio=bot_config.welcome_audio_file_id)
                            logger.info(f"✅ Áudio inicial enviado via file_id")
                            audio_sent = True
                            break
                        except Exception as audio_error:
                            if "SSL" in str(audio_error) or "TLS" in str(audio_error):
                                logger.warning(f"⚠️ Tentativa {retry_attempt + 1} falhou (SSL) para áudio: {audio_error}")
                                if retry_attempt < 2:
                                    await asyncio.sleep(2 * (retry_attempt + 1))
                                    continue
                                else:
                                    logger.error(f"❌ Todas as tentativas de envio de áudio via file_id falharam")
                            else:
                                logger.error(f"❌ Erro ao enviar áudio via file_id: {audio_error}")
                                break
                
                # Fallback para arquivo local
                if not audio_sent and bot_config.welcome_audio:
                    try:
                        with open(bot_config.welcome_audio, 'rb') as audio_file:
                            await update.message.reply_audio(audio=audio_file)
                        logger.info(f"✅ Áudio inicial enviado via arquivo local")
                        audio_sent = True
                    except Exception as local_audio_error:
                        logger.error(f"❌ Erro ao enviar áudio local: {local_audio_error}")
                
                # Log final sobre o status do áudio
                if not audio_sent and (bot_config.welcome_audio_file_id or bot_config.welcome_audio):
                    logger.warning(f"⚠️ Não foi possível enviar áudio inicial devido a problemas de conectividade. Continuando...")
            else:
                logger.info(f"⚠️ Mídia não enviada - Grupos VIP e/ou Notificações não configurados para bot {bot_config.bot_username}")
            
            # 3. Por último envia a mensagem de boas-vindas com os botões
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
            
        except Exception as e:
            logger.error(f"Erro no handler /start: {e}")
            await update.message.reply_text("Desculpe, ocorreu um erro. Tente novamente.")
    
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
            
            # Verifica se é um callback de teste de pagamento
            if callback_data.startswith('test_payment_'):
                await self._handle_test_payment(update, context)
                return
            
            # Verifica se é callback para voltar ao início
            if callback_data == 'start':
                await self._handle_start_callback(update, context)
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
            
            # Pega o nome do plano
            plan_names = bot_config.get_plan_names()
            plan_name = "Plano Especial"
            
            if plan_names and plan_index < len(plan_names):
                plan_name = plan_names[plan_index]
            else:
                # Nomes padrão
                default_names = ["🌟VIP SEMANAL🌟", "💎PREMIUM MENSAL💎", "👑ELITE ANUAL👑"]
                if plan_index < len(default_names):
                    plan_name = default_names[plan_index]
            
            # Busca o dono do bot para pegar o token PushinPay
            bot_owner = User.query.get(bot_config.user_id)

            logger.info(f"TOKEN PUSHIN: {bot_owner.pushinpay_token}")

            if not bot_owner or not bot_owner.pushinpay_token:
                await query.edit_message_text("Erro: Sistema de pagamento indisponível")
                return
            
            # Gera PIX via PushinPay
            user = update.effective_user
            description = f"Pagamento R$ {value:.2f} - Bot {bot_config.bot_username}"
            
            pix_data = self.pushinpay_service.create_pix_payment(
                user_pushinpay_token=bot_owner.pushinpay_token,
                amount=value,
                telegram_user_id=str(user.id),
                description=description
            )
            
            if not pix_data.get('success'):
                await query.edit_message_text(
                    f"❌ Erro ao gerar PIX: {pix_data.get('error', 'Erro desconhecido')}"
                )
                return
            
            # Salva pagamento no banco
            payment = Payment(
                pix_code=pix_data['pix_code'],
                amount=value,
                pix_key=pix_data.get('pix_copy_paste', ''),
                pix_qr_code=pix_data.get('qr_code', ''),
                expires_at=pix_data.get('expires_at'),
                user_id=bot_config.user_id,
                bot_id=bot_config.id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            # Cria botões para o PIX
            keyboard = [
                [InlineKeyboardButton("🔄 Verificar Pagamento", callback_data=f"check_{payment.id}")],
                [InlineKeyboardButton("🧪 TESTE - Simular Pagamento", callback_data=f"test_payment_{payment.id}")],
                [InlineKeyboardButton("🏠 Voltar ao Início", callback_data="start")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Mensagem com dados do PIX no novo formato
            pix_message = f"""🌟 Você selecionou o seguinte plano:

🎁 Plano: {plan_name}
💰 Valor: R${value:.2f}

💠 Pague via Pix Copia e Cola (ou QR Code em alguns bancos):

{pix_data.get('pix_copy_paste', 'PIX não disponível')}

👆 Toque na chave PIX acima para copiá-la

‼️ Após o pagamento, clique no botão abaixo para verificar o status:"""
            
            # Responde ao callback para confirmar a seleção
            await query.answer(f"Plano {plan_name} selecionado!")
            
            # Envia nova mensagem com as informações do PIX
            user = update.effective_user
            
            # Verifica se tem QR Code para enviar como imagem
            qr_code_data = pix_data.get('qr_code', '')
            
            if qr_code_data and qr_code_data.startswith('data:image/'):
                try:
                    # Remove o prefixo data:image/png;base64, para obter apenas o base64
                    import base64
                    from io import BytesIO
                    from PIL import Image, ImageOps
                    
                    base64_data = qr_code_data.split(',')[1] if ',' in qr_code_data else qr_code_data
                    image_data = base64.b64decode(base64_data)
                    
                    # Abre a imagem original
                    original_image = Image.open(BytesIO(image_data))
                    
                    # Adiciona padding branco ao redor do QR Code
                    padding = 20  # 20 pixels de padding
                    padded_image = ImageOps.expand(original_image, border=padding, fill='white')
                    
                    # Converte a imagem modificada de volta para bytes
                    output_buffer = BytesIO()
                    padded_image.save(output_buffer, format='PNG')
                    output_buffer.seek(0)
                    
                    # Envia nova mensagem com QR Code
                    await context.bot.send_photo(
                        chat_id=user.id,
                        photo=output_buffer,
                        caption=pix_message,
                        reply_markup=reply_markup
                    )
                    
                except Exception as img_error:
                    logger.error(f"Erro ao enviar QR Code como imagem: {img_error}")
                    # Se falhar, envia só o texto
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=pix_message,
                        reply_markup=reply_markup
                    )
            else:
                # Se não tem QR Code válido, envia só o texto
                await context.bot.send_message(
                    chat_id=user.id,
                    text=pix_message,
                    reply_markup=reply_markup
                )
            
            logger.info(f"PIX R$ {value:.2f} gerado para @{user.username if user.username else user.id} no bot {bot_config.bot_username}")
            
        except Exception as e:
            logger.error(f"Erro no handler callback: {e}")
            await query.edit_message_text("❌ Erro ao processar solicitação. Tente novamente.")
    
    async def _handle_any_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para qualquer mensagem de texto"""
        try:
            user = update.effective_user
            message_text = update.message.text
            logger.info(f"Mensagem recebida de @{user.username or user.id}: {message_text}")
            
            await update.message.reply_text(f"Recebi sua mensagem: {message_text}")
            
        except Exception as e:
            logger.error(f"Erro no handler de texto: {e}")
    
    async def _handle_start_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para callback 'start' - volta ao menu inicial"""
        try:
            # Simula um comando /start
            await self._handle_start(update, context)
        except Exception as e:
            logger.error(f"Erro no handler start callback: {e}")
    
    async def _handle_test_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para simular pagamento aprovado (APENAS PARA TESTES)"""
        try:
            query = update.callback_query
            user = update.effective_user
            
            # Extrai o ID do pagamento do callback data
            payment_id = int(query.data.split('_')[2])
            
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
            
            logger.info(f"🧪 TESTE: Simulando pagamento aprovado para @{user.username or user.id}")
            
            # Simula pagamento aprovado
            payment.status = 'approved'
            payment.paid_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"✅ TESTE: Pagamento simulado! Adicionando @{user.username or user.id} aos grupos")
            
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
            plan_name = "Plano Especial"
            plan_duration = "mensal"
            
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
            
            # Resposta ao usuário
            if success_vip:
                success_message = f"""🧪 **TESTE - PAGAMENTO SIMULADO!**

✅ Pagamento foi simulado como aprovado.
💰 Valor: R$ {payment.amount:.2f}
👑 Você foi adicionado ao grupo VIP!

🚀 Este é um teste - nenhum pagamento real foi processado."""
            else:
                success_message = f"""🧪 **TESTE - PAGAMENTO SIMULADO!**

✅ Pagamento foi simulado como aprovado.
💰 Valor: R$ {payment.amount:.2f}

⚠️ Houve um problema ao adicionar você ao grupo automaticamente.
(Verifique se os IDs dos grupos estão configurados corretamente)"""
            
            # Responde ao callback
            await query.answer("Teste de pagamento executado!")
            
            # Envia nova mensagem de teste
            keyboard = [[InlineKeyboardButton("🏠 Voltar ao Início", callback_data="start")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=user.id,
                text=success_message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"❌ Erro no teste de pagamento: {e}")
            await query.edit_message_text("❌ Erro ao simular pagamento. Tente novamente.")
    
    async def _handle_payment_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para verificação de pagamento PIX"""
        try:
            query = update.callback_query
            user = update.effective_user
            
            # Extrai o ID do pagamento do callback data
            payment_id = int(query.data.split('_')[1])
            
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
                await query.edit_message_text("❌ Sistema de pagamento indisponível.")
                return
            
            # Verifica o status do pagamento
            logger.info(f"🔍 Verificando pagamento {payment_id} para @{user.username or user.id}")
            
            # Verifica com a API do PushinPay
            try:
                pushin_service = PushinPayService()
                
                # Usa o pix_code como payment_id para verificar o status
                payment_status = pushin_service.check_payment_status(
                    bot_owner.pushinpay_token, 
                    payment.pix_code
                )
                payment_verified = payment_status.get('paid', False)
                
                logger.info(f"📊 Status do pagamento {payment.pix_code}: {payment_status}")
                
            except Exception as api_error:
                logger.error(f"❌ Erro ao verificar pagamento via API: {api_error}")
                # Em caso de erro na API, considera como não pago
                payment_verified = False
            
            if payment_verified:
                # Pagamento aprovado! 
                payment.status = 'approved'
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
                
                # Resposta ao usuário
                if success_vip:
                    success_message = f"""✅ **PAGAMENTO APROVADO!**

🎉 Parabéns! Seu pagamento foi confirmado.
💰 Valor: R$ {payment.amount:.2f}
👑 Você foi adicionado ao grupo VIP!

Aproveite o acesso exclusivo! 🚀"""
                else:
                    success_message = f"""✅ **PAGAMENTO APROVADO!**

🎉 Parabéns! Seu pagamento foi confirmado.
💰 Valor: R$ {payment.amount:.2f}

⚠️ Houve um problema ao adicionar você ao grupo automaticamente.
Entre em contato com o suporte."""
                
                # Responde ao callback
                await query.answer("Pagamento aprovado!")
                
                # Envia nova mensagem de sucesso
                keyboard = [[InlineKeyboardButton("🏠 Voltar ao Início", callback_data="start")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=user.id,
                    text=success_message,
                    reply_markup=reply_markup
                )
                
            else:
                # Pagamento ainda pendente
                await query.answer("Pagamento ainda pendente...")
                
                keyboard = [
                    [InlineKeyboardButton("🔄 Verificar Novamente", callback_data=f"check_{payment_id}")],
                    [InlineKeyboardButton("🏠 Voltar ao Início", callback_data="start")]
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
            
            # Busca informações extras do usuário
            user_info = await self._get_enhanced_user_info(bot, user)
            
            # Calcula valor líquido (assumindo 10% de taxa)
            net_value = amount * 0.9
            
            # Calcula tempo de conversão (placeholder por enquanto)
            conversion_time = "0d 0h 2m 37s"  # TODO: Implementar cálculo real
            
            # Determina categoria do plano
            plan_category = self._get_plan_category(plan_name)
            
            # Código de venda (placeholder por enquanto) 
            sale_code = "direct_access"  # TODO: Capturar do parâmetro start
            
            # Monta a notificação melhorada
            log_message = f"""🎉 Pagamento Aprovado!
🤖 Bot: @{bot_config.bot_username if bot_config else 'bot_desconhecido'}
⚙️ ID Bot: {bot_config.id if bot_config else 'N/A'}
🆔 ID Cliente: {user.id}
🔗 Username: @{user.username or 'sem_username'}
👤 Nome de Perfil: {user.first_name} {user.last_name or ''}
👤 Nome Completo: {user_info.get('full_name', 'N/A')}
💳 CPF: {user_info.get('cpf_masked', 'N/A')}
📦 Categoria: {plan_category}
🎁 Plano: {plan_name} 💎
📅 Duração: {plan_duration.title() if plan_duration else 'N/A'}
💰 Valor: R${amount:.2f}
� Valor Líquido: R${net_value:.2f}
⏳ Tempo Conversão: {conversion_time}
🔖 Código de Venda: {sale_code}
🔑 ID Transação: {payment.pix_code if payment else 'N/A'}
🏷️ ID Gateway: {user_info.get('gateway_id', 'N/A')}
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
    
    async def _get_enhanced_user_info(self, bot, user) -> dict:
        """Busca informações aprimoradas do usuário"""
        try:
            # Informações básicas do Telegram
            chat_member = await bot.get_chat_member(user.id, user.id)
            telegram_user = chat_member.user
            
            # TODO: Integrar com dados do PushinPay para obter CPF e nome completo
            return {
                'full_name': f"{telegram_user.first_name} {telegram_user.last_name or ''}".strip(),
                'cpf_masked': 'N/A',  # TODO: Obter do PushinPay
                'gateway_id': 'N/A',  # TODO: Obter do PushinPay
                'is_premium': getattr(telegram_user, 'is_premium', False),
                'language_code': getattr(telegram_user, 'language_code', 'pt-br')
            }
        except Exception as e:
            logger.error(f"Erro ao buscar info aprimorada do usuário {user.id}: {e}")
            return {
                'full_name': f"{user.first_name} {user.last_name or ''}".strip(),
                'cpf_masked': 'N/A',
                'gateway_id': 'N/A',
                'is_premium': False,
                'language_code': 'pt-br'
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