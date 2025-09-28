#!/usr/bin/env python3
"""
Script para adicionar as colunas id_vip e id_logs na tabela telegram_bots
Execute este script dentro do container Docker
"""

import sys
import os

# Adiciona o diretório src ao path
sys.path.insert(0, '/app/src')

try:
    from src.database.models import db
    from src.models.bot import TelegramBot
    from src.app import create_app
    
    # Cria a aplicação Flask
    app = create_app()
    
    with app.app_context():
        # Verifica se as colunas já existem
        try:
            # Tenta fazer uma query com as novas colunas
            result = db.engine.execute("SELECT id_vip, id_logs FROM telegram_bots LIMIT 1")
            print("✅ Colunas id_vip e id_logs já existem!")
            
        except Exception as check_error:
            print("🔧 Colunas não encontradas. Adicionando...")
            
            try:
                # Adiciona as colunas
                db.engine.execute("ALTER TABLE telegram_bots ADD COLUMN id_vip VARCHAR(255) DEFAULT NULL")
                db.engine.execute("ALTER TABLE telegram_bots ADD COLUMN id_logs VARCHAR(255) DEFAULT NULL")
                
                print("✅ Colunas id_vip e id_logs adicionadas com sucesso!")
                
                # Verifica se foram adicionadas corretamente
                result = db.engine.execute("SELECT id_vip, id_logs FROM telegram_bots LIMIT 1")
                print("✅ Verificação concluída - colunas funcionando!")
                
            except Exception as add_error:
                print(f"❌ Erro ao adicionar colunas: {add_error}")
                sys.exit(1)

except Exception as e:
    print(f"❌ Erro geral: {e}")
    sys.exit(1)

print("🎉 Migração concluída com sucesso!")