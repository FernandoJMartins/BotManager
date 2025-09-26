import pytest
from src.bot_runners.telegram_bot import TelegramBot

@pytest.fixture
def bot_instance():
    return TelegramBot(bot_token="YOUR_BOT_TOKEN")

def test_bot_initialization(bot_instance):
    assert bot_instance is not None
    assert bot_instance.bot_token == "YOUR_BOT_TOKEN"

def test_start_bot(bot_instance):
    result = bot_instance.start()
    assert result is True  # Assuming start() returns True on success

def test_stop_bot(bot_instance):
    bot_instance.start()  # Start the bot first
    result = bot_instance.stop()
    assert result is True  # Assuming stop() returns True on success

def test_bot_functionality(bot_instance):
    bot_instance.start()
    # Simulate sending a message or command to the bot
    response = bot_instance.handle_message("Test message")
    assert response is not None  # Assuming handle_message returns a response

    bot_instance.stop()