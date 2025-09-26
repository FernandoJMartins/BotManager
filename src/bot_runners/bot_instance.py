from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotInstance:
    def __init__(self, bot_config: dict):
        self.bot_config = bot_config
        self.token = bot_config["bot_token"]
        self.application = None
        self._running = False
        self._polling_task = None

    async def start_bot(self):
        if self._running:
            return True

        try:
            self.application = Application.builder().token(self.token).build()
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CallbackQueryHandler(self.payment_callback))

            await self.application.initialize()
            await self.application.start()

            self._running = True
            self._polling_task = asyncio.create_task(self._manual_polling())

            logger.info(f"Bot @{self.token} iniciado")
            return True

        except Exception as e:
            logger.error(f"Erro ao iniciar bot: {e}")
            self._running = False
            return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(f"Olá, {user.first_name}! Este é o seu bot.")

    async def payment_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("Você clicou em um botão de pagamento.")

    async def _manual_polling(self):
        offset = 0
        while self._running:
            try:
                updates = await self.application.bot.get_updates(offset=offset, timeout=10)
                for update in updates:
                    offset = update.update_id + 1
                    await self.application.process_update(update)

                if not updates:
                    await asyncio.sleep(1)

            except Exception as e:
                if self._running:
                    logger.error(f"Erro no polling: {e}")
                    await asyncio.sleep(5)

    async def stop_bot(self):
        if not self._running:
            return True

        self._running = False

        try:
            if self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass

            if self.application:
                await self.application.stop()
                await self.application.shutdown()

            logger.info("Bot parado")
            return True

        except Exception as e:
            logger.error(f"Erro ao parar bot: {e}")
            return False