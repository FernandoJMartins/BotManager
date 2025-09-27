from flask import Flask, render_template, redirect, url_for, Blueprint
from flask_login import login_required, current_user
import os
import atexit

# Importa configurações de banco
from .database.models import init_db, db
from .utils.config import load_config

# Importa blueprints das rotas
from .api.routes.auth import auth_bp
from .api.routes.bots import bots_bp
from .api.routes.webhooks import webhook_bp

# Importa serviços
from .services.bot_runner import bot_manager_service
from .services.telegram_bot_manager import bot_manager
import asyncio
import threading

def create_app():
    app = Flask(__name__)
    
    # Configurações da aplicação
    config = load_config()
    app.config.from_object(config)
    
    # Configurações específicas
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-aqui')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///telegram_bot_manager.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Cria pasta de uploads
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'audio'), exist_ok=True)
    
    # Inicializa banco de dados
    init_db(app)
    
    # Registra blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(bots_bp)
    app.register_blueprint(webhook_bp)
    
    # Rotas principais
    @app.route('/')
    def index():
        """Página inicial - redireciona conforme autenticação"""
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return redirect(url_for('auth.login'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Dashboard principal do usuário"""
        # Estatísticas do usuário
        user_stats = {
            'total_bots': len(current_user.bots),
            'active_bots': current_user.get_active_bots_count(),
            'can_add_more': current_user.can_add_bot(),
            'remaining_slots': 30 - current_user.get_active_bots_count()
        }
        
        # Bots recentes
        recent_bots = current_user.bots[:5]  # Últimos 5 bots
        
        return render_template('dashboard.html', 
                             user_stats=user_stats, 
                             recent_bots=recent_bots)
    
    # Blueprint para rotas principais
    main_bp = Blueprint('main', __name__)
    main_bp.add_url_rule('/dashboard', 'dashboard', dashboard, methods=['GET'])
    app.register_blueprint(main_bp)
    
    # Configuração de shutdown graceful
    def shutdown_handler():
        """Handler para shutdown graceful da aplicação"""
        print("Shutting down bot manager...")
        bot_manager_service.shutdown()
    
    atexit.register(shutdown_handler)
    
    # Inicia bots Telegram em thread separada
    def start_telegram_bots():
        """Inicia todos os bots Telegram ativos e mantém rodando"""
        with app.app_context():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def run_bots():
                await bot_manager.start_all_active_bots()
                # Mantém o loop rodando indefinidamente
                while True:
                    await asyncio.sleep(1)
            
            try:
                loop.run_until_complete(run_bots())
            except KeyboardInterrupt:
                print("Bot thread interrompida")
            except Exception as e:
                print(f"Erro na thread do bot: {e}")
            finally:
                loop.close()
    
    # Thread para rodar os bots Telegram
    bot_thread = threading.Thread(target=start_telegram_bots, daemon=True)
    bot_thread.start()
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    try:
        print("🚀 Iniciando Telegram Bot Manager...")
        print("📊 Dashboard disponível em: http://localhost:5000")
        print("🤖 Sistema de bots 24/7 ativo")
        
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n⏹️  Parando aplicação...")
        bot_manager_service.shutdown()
    except Exception as e:
        print(f"❌ Erro ao iniciar aplicação: {e}")
        bot_manager_service.shutdown()