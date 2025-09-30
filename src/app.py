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
        from flask import request
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        from .models.bot import TelegramBot as Bot
        from .models.client import User as Client
        from .models.payment import Payment
        
        # Parâmetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date') 
        bot_id = request.args.get('bot_id')
        
        # Datas padrão (últimos 30 dias)
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # Filtro de bots
        bot_filter = []
        if bot_id:
            bot_filter.append(Bot.id == bot_id)
        bot_filter.append(Bot.user_id == current_user.id)
        
        # Query base para métricas
        base_date_filter = and_(
            func.date(Payment.created_at) >= start_date,
            func.date(Payment.created_at) <= end_date
        )
        
        # Métricas principais
        stats = {}
        
        # 1. Bots do usuário
        user_bots = db.session.query(Bot).filter(Bot.user_id == current_user.id)
        if bot_id:
            user_bots = user_bots.filter(Bot.id == bot_id)
        bots_count = user_bots.count()
        
        # 2. Iniciações do bot (/start) - usar count de bots como proxy
        stats['bot_starts'] = user_bots.filter(Bot.is_active == True).count()
        
        # 3. Assinaturas ativas - usar count de pagamentos aprovados como proxy
        stats['subscriptions'] = db.session.query(func.count(Payment.id))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(*bot_filter, Payment.status == 'completed'))\
            .scalar() or 0
            
        # 4. Sessões ativas - usar bots rodando como proxy
        stats['active_sessions'] = user_bots.filter(and_(Bot.is_active == True, Bot.is_running == True)).count()
        
        # 5. Faturamento total (soma dos pagamentos aprovados menos taxas)
        total_payments = db.session.query(func.sum(Payment.amount))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'completed',
                func.date(Payment.created_at) >= start_date,
                func.date(Payment.created_at) <= end_date
            )).scalar() or 0
        
        # Calcular taxas (assumindo 5% de taxa)
        fees = total_payments * 0.05
        stats['total_revenue'] = f"{(total_payments - fees):.2f}"
        
        # Cálculas de mudança percentual (usar valores placeholders por enquanto)
        stats['bot_starts_change'] = 12.5  # Placeholder
        stats['subscriptions_change'] = 5.2  # Placeholder
        stats['sessions_change'] = 8.1  # Placeholder
        stats['revenue_change'] = 9.18  # Placeholder
        stats['session_percentage'] = round((stats['active_sessions'] / max(stats['bot_starts'], 1)) * 100, 1)
        
        # Dados para gráficos baseados nos pagamentos reais
        monthly_data = db.session.query(
            func.to_char(Payment.created_at, 'YYYY-MM').label('month'),
            func.sum(Payment.amount).label('total')
        ).join(Bot, Payment.bot_id == Bot.id)\
        .filter(and_(*bot_filter, Payment.status == 'completed'))\
        .group_by(func.to_char(Payment.created_at, 'YYYY-MM'))\
        .order_by('month').all()
        
        # Preparar dados do gráfico
        if monthly_data:
            revenue_labels = [data.month for data in monthly_data]
            revenue_data = [float(data.total or 0) for data in monthly_data]
            fees_data = [amount * 0.05 for amount in revenue_data]
        else:
            # Dados placeholder se não houver pagamentos
            revenue_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
            revenue_data = [100, 150, 120, 200, 180, 250]
            fees_data = [5, 7.5, 6, 10, 9, 12.5]
        
        chart_data = {
            'revenue_labels': revenue_labels,
            'revenue_data': revenue_data,
            'fees_data': fees_data,
            'sessions_labels': ['10h', '14h', '18h', '22h'],
            'sessions_data': [stats['active_sessions'], stats['active_sessions']+10, stats['active_sessions']+5, stats['active_sessions']+8]
        }
        
        # Lista de bots para o filtro
        bots = Bot.query.filter_by(user_id=current_user.id).all()
        
        # Debug: vamos usar dados simples primeiro
        simple_stats = {
            'bot_starts': 5,
            'subscriptions': 3, 
            'active_sessions': 2,
            'total_revenue': '150.00',
            'bot_starts_change': 10.0,
            'subscriptions_change': 5.0,
            'sessions_change': 8.0,
            'revenue_change': 12.0,
            'session_percentage': 40.0
        }
        
        simple_chart = {
            'revenue_labels': ['Jan', 'Fev', 'Mar'],
            'revenue_data': [100, 150, 200],
            'fees_data': [5, 7.5, 10],
            'sessions_labels': ['10h', '14h', '18h'],
            'sessions_data': [1, 2, 3]
        }
        
        return render_template('dashboard.html', 
                             stats=simple_stats,
                             chart_data=simple_chart,
                             bots=bots,
                             start_date=start_date,
                             end_date=end_date,
                             period_label=f"{start_date} até {end_date}")
    
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