"""
Migração para adicionar informações do usuário do Telegram à tabela de pagamentos
Data: 2025-10-01
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src.database.models import db
import os

def upgrade():
    """Adiciona colunas para armazenar informações do usuário do Telegram"""
    
    # Conecta ao banco de dados
    try:
        # Adiciona colunas para informações do usuário do Telegram
        with db.engine.connect() as conn:
            # Verifica se as colunas já existem antes de tentar criar
            result = conn.execute("PRAGMA table_info(payments)")
            existing_columns = [row[1] for row in result.fetchall()]
            
            if 'telegram_user_id' not in existing_columns:
                conn.execute("ALTER TABLE payments ADD COLUMN telegram_user_id BIGINT")
                print("✅ Coluna telegram_user_id adicionada")
            else:
                print("⚠️ Coluna telegram_user_id já existe")
            
            if 'telegram_username' not in existing_columns:
                conn.execute("ALTER TABLE payments ADD COLUMN telegram_username VARCHAR(100)")
                print("✅ Coluna telegram_username adicionada")
            else:
                print("⚠️ Coluna telegram_username já existe")
            
            if 'telegram_first_name' not in existing_columns:
                conn.execute("ALTER TABLE payments ADD COLUMN telegram_first_name VARCHAR(100)")
                print("✅ Coluna telegram_first_name adicionada")
            else:
                print("⚠️ Coluna telegram_first_name já existe")
            
            if 'telegram_last_name' not in existing_columns:
                conn.execute("ALTER TABLE payments ADD COLUMN telegram_last_name VARCHAR(100)")
                print("✅ Coluna telegram_last_name adicionada")
            else:
                print("⚠️ Coluna telegram_last_name já existe")
            
            conn.commit()
            print("✅ Migração concluída com sucesso!")
            
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        raise

def downgrade():
    """Remove as colunas adicionadas (rollback)"""
    try:
        with db.engine.connect() as conn:
            # SQLite não suporte DROP COLUMN diretamente, então precisamos recriar a tabela
            print("⚠️ SQLite não suporta DROP COLUMN. Para fazer rollback, você precisará:")
            print("1. Fazer backup dos dados")
            print("2. Recriar a tabela sem essas colunas")
            print("3. Restaurar os dados")
            
    except Exception as e:
        print(f"❌ Erro no rollback: {e}")
        raise

if __name__ == "__main__":
    # Para testar a migração diretamente
    from src.app import create_app
    
    app = create_app()
    with app.app_context():
        upgrade()