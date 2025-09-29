#!/usr/bin/env python3

"""
Migração para adicionar campos de file_id para mídia do Telegram
e manter compatibilidade com arquivos locais existentes
"""

import sys
import os
sys.path.append('/app')

from src.database.models import db
from src.app import create_app
from sqlalchemy import text

def migrate_media_fields():
    """Adiciona campos para armazenar file_id do Telegram"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Iniciando migração dos campos de mídia...")
            
            # Adiciona novos campos para file_id
            migration_queries = [
                # Campos para file_id do Telegram
                "ALTER TABLE telegram_bots ADD COLUMN IF NOT EXISTS welcome_image_file_id VARCHAR(255);",
                "ALTER TABLE telegram_bots ADD COLUMN IF NOT EXISTS welcome_audio_file_id VARCHAR(255);",
                "ALTER TABLE telegram_bots ADD COLUMN IF NOT EXISTS welcome_video_file_id VARCHAR(255);",
                
                # Campo para identificar o bot na mensagem (evita cruzamento de dados)
                "ALTER TABLE telegram_bots ADD COLUMN IF NOT EXISTS media_identifier VARCHAR(100);",
                
                # Comentários para documentação
                "COMMENT ON COLUMN telegram_bots.welcome_image_file_id IS 'File ID da imagem no Telegram';",
                "COMMENT ON COLUMN telegram_bots.welcome_audio_file_id IS 'File ID do áudio no Telegram';",
                "COMMENT ON COLUMN telegram_bots.welcome_video_file_id IS 'File ID do vídeo no Telegram';",
                "COMMENT ON COLUMN telegram_bots.media_identifier IS 'Identificador único para mídia do bot';",
            ]
            
            for query in migration_queries:
                try:
                    db.session.execute(text(query))
                    print(f"✅ Executado: {query[:50]}...")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                        print(f"⚠️  Campo já existe: {query[:50]}...")
                    else:
                        print(f"❌ Erro: {e}")
            
            db.session.commit()
            
            # Gera identificadores únicos para bots existentes
            from src.models.bot import TelegramBot
            import uuid
            
            bots_without_identifier = TelegramBot.query.filter(
                (TelegramBot.media_identifier.is_(None)) | 
                (TelegramBot.media_identifier == '')
            ).all()
            
            for bot in bots_without_identifier:
                bot.media_identifier = f"bot_{bot.id}_{str(uuid.uuid4())[:8]}"
                print(f"🔖 Bot '{bot.bot_name}' recebeu identificador: {bot.media_identifier}")
            
            db.session.commit()
            
            print("✅ Migração concluída com sucesso!")
            print(f"📊 Total de bots atualizados: {len(bots_without_identifier)}")
            
        except Exception as e:
            print(f"❌ Erro durante migração: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_media_fields()