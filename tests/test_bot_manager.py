import unittest
from src.services.bot_manager import BotManager
from src.models.client import Client
from src.models.bot import Bot

class TestBotManager(unittest.TestCase):
    
    def setUp(self):
        self.client = Client(client_id="test_client")
        self.bot_manager = BotManager(client=self.client)

    def test_add_bot(self):
        bot = Bot(bot_id="test_bot", bot_token="123456:ABC-DEF1234ghIkl-zyx57W2P0s")
        self.bot_manager.add_bot(bot)
        self.assertIn(bot, self.client.bots)

    def test_remove_bot(self):
        bot = Bot(bot_id="test_bot", bot_token="123456:ABC-DEF1234ghIkl-zyx57W2P0s")
        self.bot_manager.add_bot(bot)
        self.bot_manager.remove_bot(bot.bot_id)
        self.assertNotIn(bot, self.client.bots)

    def test_start_bot(self):
        bot = Bot(bot_id="test_bot", bot_token="123456:ABC-DEF1234ghIkl-zyx57W2P0s")
        self.bot_manager.add_bot(bot)
        self.bot_manager.start_bot(bot.bot_id)
        self.assertTrue(bot.is_running)

    def test_stop_bot(self):
        bot = Bot(bot_id="test_bot", bot_token="123456:ABC-DEF1234ghIkl-zyx57W2P0s")
        self.bot_manager.add_bot(bot)
        self.bot_manager.start_bot(bot.bot_id)
        self.bot_manager.stop_bot(bot.bot_id)
        self.assertFalse(bot.is_running)

if __name__ == '__main__':
    unittest.main()