from flask import request, jsonify
from src.models.bot import Bot
from src.utils.logger import Logger

class WebhookService:
    def __init__(self, bot_manager):
        self.bot_manager = bot_manager
        self.logger = Logger()

    def set_webhook(self, bot_id, webhook_url):
        bot = self.bot_manager.get_bot(bot_id)
        if bot:
            success = bot.set_webhook(webhook_url)
            if success:
                self.logger.info(f"Webhook set for bot {bot_id} to {webhook_url}")
                return jsonify({"message": "Webhook set successfully"}), 200
            else:
                self.logger.error(f"Failed to set webhook for bot {bot_id}")
                return jsonify({"error": "Failed to set webhook"}), 500
        else:
            self.logger.error(f"Bot {bot_id} not found")
            return jsonify({"error": "Bot not found"}), 404

    def delete_webhook(self, bot_id):
        bot = self.bot_manager.get_bot(bot_id)
        if bot:
            success = bot.delete_webhook()
            if success:
                self.logger.info(f"Webhook deleted for bot {bot_id}")
                return jsonify({"message": "Webhook deleted successfully"}), 200
            else:
                self.logger.error(f"Failed to delete webhook for bot {bot_id}")
                return jsonify({"error": "Failed to delete webhook"}), 500
        else:
            self.logger.error(f"Bot {bot_id} not found")
            return jsonify({"error": "Bot not found"}), 404

    def handle_webhook(self, bot_id):
        bot = self.bot_manager.get_bot(bot_id)
        if bot:
            update = request.json
            bot.process_update(update)
            return jsonify({"message": "Update processed"}), 200
        else:
            self.logger.error(f"Bot {bot_id} not found for webhook handling")
            return jsonify({"error": "Bot not found"}), 404