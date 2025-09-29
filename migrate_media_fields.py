#!/usr/bin/env python3
"""
Migração: Adiciona campos file_id para mídia do Telegram
Data: 2025-09-28
"""

import sys
import os
sys.path.append('/app')

from src.database.models import db
from src.app import create_app

def migrate_media_fields():
    """Adiciona campos file_id para armazenar mídia do Telegram"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Adiciona novas colunas para file_id
            db.engine.execute("""
                ALTER TABLE telegram_bots 
                ADD COLUMN welcome_image_file_id VARCHAR(255);
            """)
            
            db.engine.execute("""
                ALTER TABLE telegram_bots 
                ADD COLUMN welcome_audio_file_id VARCHAR(255);
            """)
            
            db.engine.execute("""
                ALTER TABLE telegram_bots 
                ADD COLUMN welcome_video_file_id VARCHAR(255);
            """)
            
            print("✅ Migração concluída: Campos file_id adicionados com sucesso!")
            
            # Lista as colunas da tabela para confirmar
            result = db.engine.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'telegram_bots' 
                AND column_name LIKE '%file_id%';
            """)
            
            columns = [row[0] for row in result]
            print(f"📊 Novas colunas criadas: {columns}")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            # Se a coluna já existe, não é erro crítico
            if "already exists" in str(e).lower():
                print("ℹ️  Colunas já existem, migração não necessária")
            else:
                raise e

if __name__ == "__main__":
    migrate_media_fields()