"""
Migração para criar a tabela codigo_venda
Execute este script para adicionar a nova tabela ao banco de dados existente
"""
import sys
import os

# Adiciona o diretório raiz ao path para permitir imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.models import db
from src.models.codigo_venda import CodigoVenda

def create_codigo_venda_table():
    """Cria a tabela codigo_venda se ela não existir"""
    try:
        # Cria a tabela se ela não existir
        db.create_all()
        print("✅ Tabela 'codigo_venda' criada com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro ao criar tabela 'codigo_venda': {e}")
        return False

if __name__ == "__main__":
    from src.app import create_app
    
    app = create_app()
    with app.app_context():
        create_codigo_venda_table()