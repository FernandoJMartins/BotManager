#!/usr/bin/env python3

"""
Script para debugar os valores PIX de um bot específico
"""

import sys
import os
sys.path.append('/app')

from src.models.bot import TelegramBot
from src.database.models import db
from src.app import create_app

def debug_bot_values(bot_id):
    app = create_app()
    
    with app.app_context():
        bot = TelegramBot.query.get(bot_id)
        
        if not bot:
            print(f"❌ Bot com ID {bot_id} não encontrado")
            return
            
        print(f"🤖 Bot: {bot.bot_name} (ID: {bot.id})")
        print(f"📊 Dados brutos do banco:")
        print(f"   - pix_values: {bot.pix_values} (tipo: {type(bot.pix_values)})")
        print(f"   - plan_names: {bot.plan_names} (tipo: {type(bot.plan_names)})")
        
        print(f"\n🔧 Dados processados pelos métodos:")
        print(f"   - get_pix_values(): {bot.get_pix_values()}")
        print(f"   - get_plan_names(): {bot.get_plan_names()}")
        
        print(f"\n✅ Status:")
        print(f"   - is_active: {bot.is_active}")
        print(f"   - is_running: {bot.is_running}")
        print(f"   - is_fully_configured: {bot.is_fully_configured()}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python debug_bot.py <bot_id>")
        sys.exit(1)
    
    try:
        bot_id = int(sys.argv[1])
        debug_bot_values(bot_id)
    except ValueError:
        print("❌ ID do bot deve ser um número")
        sys.exit(1)