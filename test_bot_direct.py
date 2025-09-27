#!/usr/bin/env python3
"""
Teste direto do bot Telegram sem Flask
Para verificar se o problema é no polling ou na integração
"""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token do bot (mesmo que está sendo usado no sistema)
BOT_TOKEN = "8264015680:AAHuZT4ROwTjLBNvxkBE-NDV9JEjYX9V73M"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /start"""
    user = update.effective_user
    logger.info(f"🚀 TESTE - Comando /start recebido de {user.username or user.id}")
    
    await update.message.reply_text(
        f"🎉 FUNCIONOU! Olá {user.first_name}!\n\n"
        "Este é um teste direto do bot.\n"
        "Se você está vendo esta mensagem, significa que o polling está funcionando!"
    )
    
    print(f"✅ SUCESSO - Resposta enviada para {user.username or user.id}")

async def main():
    """Função principal"""
    print("🤖 Iniciando teste direto do bot...")
    
    # Criar aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Adicionar handler
    application.add_handler(CommandHandler("start", start_command))
    
    # Inicializar e iniciar
    print("📡 Iniciando polling...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    print("✅ Bot está rodando! Envie /start no Telegram")
    print("⏹️  Pressione Ctrl+C para parar")
    
    # Manter rodando
    try:
        # Aguarda até ser interrompido
        await application.updater.idle()
    except KeyboardInterrupt:
        print("🛑 Parando bot...")
    finally:
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())