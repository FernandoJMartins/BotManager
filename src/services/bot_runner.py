import threading
import time
import asyncio
from datetime import datetime
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError
from ..models.bot import TelegramBot
from ..models.payment import Payment
from ..database.models import db
from ..services.pushinpay_service import pushinpay_service
import json
import logging

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramBotRunner:
    """Classe para executar um bot individual do Telegram"""
    
    def __init__(self, bot_config: TelegramBot):
        self.bot_config = bot_config
        self.application = None
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self):
        """Inicia o bot em thread separada"""
        if self.is_running:
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_bot)
        self._thread.daemon = True
        self._thread.start()
        self.is_running = True
        
        # Atualiza status no banco
        self.bot_config.is_running = True
        self.bot_config.last_activity = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Bot {self.bot_config.bot_username} iniciado")
    
    def stop(self):
        """Para o bot"""
        if not self.is_running:
            return
        
        self._stop_event.set()
        if self.application:
            asyncio.run(self.application.stop())
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.is_running = False
        
        # Atualiza status no banco
        self.bot_config.is_running = False
        db.session.commit()
        
        logger.info(f"Bot {self.bot_config.bot_username} parado")
    
    def _run_bot(self):
        """Executa o bot em loop assíncrono"""
        try:
            asyncio.run(self._async_run())
        except Exception as e:
            logger.error(f"Erro ao executar bot {self.bot_config.bot_username}: {e}")
            self.is_running = False
            self.bot_config.is_running = False
            db.session.commit()
    
    async def _async_run(self):
        """Loop assíncrono do bot"""
        # Cria aplicação do bot
        self.application = Application.builder().token(self.bot_config.bot_token).build()
        
        # Adiciona handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("pix", self._handle_pix))
        self.application.add_handler(CallbackQueryHandler(self._handle_pix_callback, pattern="^pix_"))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Inicia o bot
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Mantém rodando até receber sinal de parada
        while not self._stop_event.is_set():
            await asyncio.sleep(1)
            
            # Atualiza última atividade
            self.bot_config.last_activity = datetime.utcnow()
            db.session.commit()
        
        # Para o bot
        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /start"""
        try:
            # Envia mensagem de boas-vindas
            if self.bot_config.welcome_message:
                await update.message.reply_text(self.bot_config.welcome_message)
            
            # Envia imagem de boas-vindas se configurada
            if self.bot_config.welcome_image:
                try:
                    with open(self.bot_config.welcome_image, 'rb') as photo:
                        await update.message.reply_photo(photo=photo)
                except Exception as e:
                    logger.error(f"Erro ao enviar imagem: {e}")
            
            # Envia áudio de boas-vindas se configurado
            if self.bot_config.welcome_audio:
                try:
                    with open(self.bot_config.welcome_audio, 'rb') as audio:
                        await update.message.reply_audio(audio=audio)
                except Exception as e:
                    logger.error(f"Erro ao enviar áudio: {e}")
            
            # Envia botões PIX se configurados
            await self._send_pix_buttons(update)
            
        except Exception as e:
            logger.error(f"Erro no handler /start: {e}")
    
    async def _handle_pix(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comando /pix - gera PIX com valores configurados"""
        try:
            if not self.bot_config.pix_values:
                await update.message.reply_text("Valores PIX não configurados.")
                return
            
            # Parse dos valores PIX
            try:
                pix_values = json.loads(self.bot_config.pix_values)
            except:
                await update.message.reply_text("Erro na configuração dos valores PIX.")
                return
            
            if not pix_values:
                await update.message.reply_text("Nenhum valor PIX configurado.")
                return
            
            # Monta mensagem com valores disponíveis
            message = "💰 Valores disponíveis para PIX:\n\n"
            for i, value in enumerate(pix_values, 1):
                message += f"{i}. R$ {value:.2f}\n"
            
            message += "\nDigite o número correspondiente ao valor desejado."
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Erro no handler /pix: {e}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para mensagens de texto"""
        try:
            text = update.message.text.strip()
            
            # Verifica se é seleção de valor PIX
            if text.isdigit():
                if not self.bot_config.pix_values:
                    return
                
                try:
                    pix_values = json.loads(self.bot_config.pix_values)
                    value_index = int(text) - 1
                    
                    if 0 <= value_index < len(pix_values):
                        selected_value = pix_values[value_index]
                        
                        # Aqui você integraria com seu sistema de PIX
                        # Por enquanto, apenas informa o valor selecionado
                        message = f"✅ Valor selecionado: R$ {selected_value:.2f}\n\n"
                        message += "🔄 Gerando PIX...\n"
                        message += "💳 Chave PIX: seu@email.com\n"  # Substitua pela sua chave
                        message += f"💰 Valor: R$ {selected_value:.2f}"
                        
                        await update.message.reply_text(message)
                    else:
                        await update.message.reply_text("Número inválido. Digite /pix para ver as opções.")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar valor PIX: {e}")
            
        except Exception as e:
            logger.error(f"Erro no handler de mensagem: {e}")
    
    async def _send_pix_buttons(self, update: Update):
        """Envia botões inline com valores PIX configurados"""
        try:
            if not self.bot_config.pix_values:
                return
            
            # Parse dos valores PIX
            try:
                pix_values = json.loads(self.bot_config.pix_values)
            except:
                return
            
            if not pix_values:
                return
            
            # Cria botões inline
            keyboard = []
            for i, value in enumerate(pix_values):
                button_text = f"💰 R$ {value:.2f}"
                callback_data = f"pix_{i}_{value}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "💳 *Valores disponíveis para PIX:*\n\nEscolha um valor abaixo:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Erro ao enviar botões PIX: {e}")
    
    async def _handle_pix_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para callback dos botões PIX"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Parse do callback data
            callback_data = query.data
            if not callback_data.startswith('pix_'):
                return
            
            parts = callback_data.split('_')
            if len(parts) != 3:
                return
            
            value_index = int(parts[1])
            selected_value = float(parts[2])
            
            # Busca o usuário dono do bot
            user = self.bot_config.owner
            
            if not user.pushinpay_token:
                await query.edit_message_text(
                    "❌ Token PushinPay não configurado.\n"
                    "Entre em contato com o administrador do bot."
                )
                return
            
            # Gera cobrança PIX via PushinPay
            await query.edit_message_text("🔄 Gerando PIX... Aguarde...")
            
            pix_result = pushinpay_service.create_pix_payment(
                user_pushinpay_token=user.pushinpay_token,
                user_id=user.id,
                bot_id=self.bot_config.id,
                description=f"PIX Bot Telegram - R$ {selected_value:.2f}"
            )
            
            if pix_result['success']:
                message = f"✅ *PIX Gerado com Sucesso!*\n\n"
                message += f"💰 Valor: R$ {selected_value:.2f}\n"
                message += f"🔢 Código: `{pix_result['pix_code']}`\n\n"
                message += f"📋 *Pix Copia e Cola:*\n"
                message += f"`{pix_result['pix_copy_paste']}`\n\n"
                message += "✨ Após o pagamento, você receberá confirmação automaticamente!"
                
                await query.edit_message_text(message, parse_mode='Markdown')
                
                # Se houver QR code, envia separadamente
                if pix_result.get('qr_code'):
                    await query.message.reply_text(
                        f"📱 *QR Code PIX:*\n{pix_result['qr_code']}",
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text(
                    f"❌ Erro ao gerar PIX:\n{pix_result.get('error', 'Erro desconhecido')}"
                )
            
        except Exception as e:
            logger.error(f"Erro no callback PIX: {e}")
            try:
                await query.edit_message_text("❌ Erro ao processar PIX. Tente novamente.")
            except:
                pass

class BotManagerService:
    """Gerenciador principal de todos os bots - Novo nome para evitar conflito"""
    
    def __init__(self):
        self.active_bots = {}  # bot_id -> TelegramBotRunner
        self._monitor_thread = None
        self._stop_monitoring = threading.Event()
        self.start_monitoring()
    
    def start_monitoring(self):
        """Inicia o monitoramento contínuo dos bots"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_bots)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()
        
        logger.info("Sistema de monitoramento de bots iniciado")
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        self._stop_monitoring.set()
        if self._monitor_thread:
            self._monitor_thread.join()
    
    def _monitor_bots(self):
        """Loop de monitoramento dos bots"""
        while not self._stop_monitoring.is_set():
            try:
                # Busca bots que deveriam estar rodando
                active_bots = TelegramBot.query.filter_by(
                    is_active=True
                ).all()
                
                for bot_config in active_bots:
                    # Verifica se bot está rodando
                    if bot_config.id not in self.active_bots:
                        # Bot não está rodando, inicia
                        self.start_bot(bot_config)
                    elif not self.active_bots[bot_config.id].is_running:
                        # Bot parou, reinicia
                        logger.warning(f"Bot {bot_config.bot_username} parou, reiniciando...")
                        self.restart_bot(bot_config)
                
                # Remove bots que não deveriam estar rodando
                for bot_id, bot_runner in list(self.active_bots.items()):
                    bot_config = TelegramBot.query.get(bot_id)
                    if not bot_config or not bot_config.is_active:
                        self.stop_bot(bot_id)
                
                # Aguarda antes da próxima verificação
                time.sleep(30)  # Verifica a cada 30 segundos
                
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
                time.sleep(60)  # Aguarda mais tempo em caso de erro
    
    def start_bot(self, bot_config: TelegramBot):
        """Inicia um bot específico"""
        try:
            if bot_config.id in self.active_bots:
                return False  # Bot já está rodando
            

            
            # Cria runner do bot
            bot_runner = TelegramBotRunner(bot_config)
            bot_runner.start()
            
            self.active_bots[bot_config.id] = bot_runner
            
            logger.info(f"Bot {bot_config.bot_username} iniciado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar bot {bot_config.bot_username}: {e}")
            return False
    
    def stop_bot(self, bot_id: int):
        """Para um bot específico"""
        try:
            if bot_id not in self.active_bots:
                return False
            
            bot_runner = self.active_bots[bot_id]
            bot_runner.stop()
            
            del self.active_bots[bot_id]
            
            logger.info(f"Bot {bot_id} parado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar bot {bot_id}: {e}")
            return False
    
    def restart_bot(self, bot_config: TelegramBot):
        """Reinicia um bot"""
        self.stop_bot(bot_config.id)
        time.sleep(2)  # Aguarda um pouco antes de reiniciar
        return self.start_bot(bot_config)
    
    def get_bot_status(self, bot_id: int):
        """Obtém status de um bot"""
        if bot_id in self.active_bots:
            return {
                'running': self.active_bots[bot_id].is_running,
                'status': 'active'
            }
        return {
            'running': False,
            'status': 'inactive'
        }
    
    def list_active_bots(self):
        """Lista todos os bots ativos"""
        return list(self.active_bots.keys())
    
    def shutdown(self):
        """Para todos os bots e o sistema de monitoramento"""
        logger.info("Iniciando shutdown do sistema...")
        
        # Para monitoramento
        self.stop_monitoring()
        
        # Para todos os bots
        for bot_id in list(self.active_bots.keys()):
            self.stop_bot(bot_id)
        
        logger.info("Shutdown completo")

# Instância global do gerenciador
bot_manager_service = BotManagerService()