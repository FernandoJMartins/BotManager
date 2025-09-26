import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    DATABASE_URI = os.getenv("DATABASE_URI")
    TELEGRAM_API_URL = "https://api.telegram.org/bot"
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    pass

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig
}

def load_config():
    """Load configuration based on environment."""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)