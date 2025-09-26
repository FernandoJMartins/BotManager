#!/usr/bin/env python3
"""
Script de inicialização do Telegram Bot Manager
Este script configura e inicia a aplicação automaticamente
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header():
    """Imprime o cabeçalho da aplicação"""
    print("=" * 60)
    print("🤖 TELEGRAM BOT MANAGER")
    print("Sistema de Hospedagem de Bots 24/7")
    print("=" * 60)
    print()

def check_python_version():
    """Verifica se a versão do Python é compatível"""
    if sys.version_info < (3, 8):
        print("❌ Erro: Python 3.8+ é necessário")
        print(f"   Versão atual: {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")

def install_dependencies():
    """Instala as dependências do projeto"""
    print("\n📦 Instalando dependências...")
    
    try:
        # Verifica se requirements.txt existe
        if not Path("requirements.txt").exists():
            print("❌ Arquivo requirements.txt não encontrado")
            sys.exit(1)
        
        # Instala dependências
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependências instaladas com sucesso")
        else:
            print("❌ Erro ao instalar dependências:")
            print(result.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        sys.exit(1)

def setup_environment():
    """Configura variáveis de ambiente"""
    print("\n🔧 Configurando ambiente...")
    
    # Cria arquivo .env se não existir
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Criando arquivo .env...")
        
        env_content = """# Configurações do Telegram Bot Manager
SECRET_KEY=sua-chave-secreta-muito-segura-aqui-change-me
DATABASE_URL=sqlite:///telegram_bot_manager.db
PIX_KEY=sua@chave.pix

# Configurações opcionais
DEBUG=False
FLASK_ENV=production
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
"""
        
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        
        print("✅ Arquivo .env criado")
        print("⚠️  IMPORTANTE: Edite o arquivo .env com suas configurações reais!")
    else:
        print("✅ Arquivo .env já existe")

def create_directories():
    """Cria diretórios necessários"""
    print("\n📁 Criando diretórios...")
    
    directories = [
        "uploads",
        "uploads/images",
        "uploads/audio",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Diretório criado: {directory}")

def initialize_database():
    """Inicializa o banco de dados"""
    print("\n🗄️  Inicializando banco de dados...")
    
    try:
        # Importa e inicializa o app para criar as tabelas
        sys.path.insert(0, str(Path("src").absolute()))
        from src.app import create_app
        
        app = create_app()
        with app.app_context():
            print("✅ Banco de dados inicializado")
            
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        print("   O banco será criado automaticamente no primeiro acesso")

def print_instructions():
    """Imprime instruções finais"""
    print("\n" + "=" * 60)
    print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print()
    print("📋 PRÓXIMOS PASSOS:")
    print()
    print("1. 📝 Edite o arquivo .env com suas configurações:")
    print("   - SECRET_KEY: Chave secreta única")
    print("   - PIX_KEY: Sua chave PIX para recebimentos")
    print()
    print("2. 🚀 Inicie a aplicação:")
    print("   python src/app.py")
    print()
    print("3. 🌐 Acesse o dashboard:")
    print("   http://localhost:5000")
    print()
    print("4. 📱 Para criar bots:")
    print("   - Obtenha tokens no @BotFather do Telegram")
    print("   - Registre-se na aplicação")
    print("   - Crie e configure seus bots")
    print()
    print("💡 DICAS:")
    print("   - Cada bot custa R$ 0,70")
    print("   - Limite de 30 bots por usuário")
    print("   - Bots rodam 24/7 automaticamente")
    print()
    print("📚 Para mais informações, consulte o README.md")
    print("=" * 60)

def main():
    """Função principal"""
    print_header()
    
    print("🔍 Verificando sistema...")
    check_python_version()
    
    install_dependencies()
    setup_environment()
    create_directories()
    initialize_database()
    
    print_instructions()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        sys.exit(1)