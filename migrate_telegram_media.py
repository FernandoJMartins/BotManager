#!/usr/bin/env python3

"""
Migração para alterar campos de mídia para armazenar file_id do Telegram
em vez de caminhos de arquivos locais
"""

import sys
import os
sys.path.append('/app')

from src.database.models import db
from src.app import create_app

def migrate_media_fields():
    """Altera os campos de mídia para suportar file_id do Telegram"""
    app = create_app()
    
    with app.app_context():
        try:
            # SQL para alterar os campos de mídia
            migration_sql = """
            -- Renomeia colunas antigas para backup
            ALTER TABLE telegram_bots RENAME COLUMN welcome_image TO welcome_image_old;
            ALTER TABLE telegram_bots RENAME COLUMN welcome_audio TO welcome_audio_old;
            
            -- Cria novas colunas para file_id do Telegram
            ALTER TABLE telegram_bots ADD COLUMN welcome_image_file_id VARCHAR(255);
            ALTER TABLE telegram_bots ADD COLUMN welcome_audio_file_id VARCHAR(255);
            
            -- Adiciona colunas para metadados da mídia
            ALTER TABLE telegram_bots ADD COLUMN welcome_image_type VARCHAR(50);
            ALTER TABLE telegram_bots ADD COLUMN welcome_audio_type VARCHAR(50);
            ALTER TABLE telegram_bots ADD COLUMN welcome_image_size INTEGER;
            ALTER TABLE telegram_bots ADD COLUMN welcome_audio_size INTEGER;
            """
            
            # Executa a migração
            db.engine.execute(migration_sql)
            db.session.commit()
            
            print("✅ Migração concluída com sucesso!")
            print("📊 Novos campos criados:")
            print("   - welcome_image_file_id: File ID do Telegram para imagem")
            print("   - welcome_audio_file_id: File ID do Telegram para áudio")
            print("   - welcome_image_type: Tipo do arquivo (image/jpeg, etc)")
            print("   - welcome_audio_type: Tipo do arquivo (audio/mpeg, etc)")
            print("   - welcome_image_size: Tamanho do arquivo em bytes")
            print("   - welcome_audio_size: Tamanho do arquivo em bytes")
            print("📦 Campos antigos preservados como backup (*_old)")
            
        except Exception as e:
            print(f"❌ Erro na migração: {e}")
            db.session.rollback()
            return False
            
    return True

if __name__ == "__main__":
    success = migrate_media_fields()
    if success:
        print("\n🚀 Migração completa! Agora você pode usar file_id do Telegram para mídia.")
    else:
        print("\n💥 Falha na migração. Verifique os logs acima.")