"""
Migração para adicionar colunas id_vip e id_logs na tabela telegram_bots
"""

from flask_migrate import Migrate
from ..models import db

def upgrade():
    """Adiciona as colunas id_vip e id_logs"""
    try:
        # SQL para adicionar as colunas
        db.engine.execute("""
            ALTER TABLE telegram_bots 
            ADD COLUMN id_vip VARCHAR(255) DEFAULT NULL,
            ADD COLUMN id_logs VARCHAR(255) DEFAULT NULL;
        """)
        
        print("✅ Colunas id_vip e id_logs adicionadas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao adicionar colunas: {e}")
        raise

def downgrade():
    """Remove as colunas id_vip e id_logs"""
    try:
        # SQL para remover as colunas
        db.engine.execute("""
            ALTER TABLE telegram_bots 
            DROP COLUMN id_vip,
            DROP COLUMN id_logs;
        """)
        
        print("✅ Colunas id_vip e id_logs removidas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao remover colunas: {e}")
        raise

if __name__ == "__main__":
    print("Executando migração para adicionar colunas de grupos...")
    upgrade()