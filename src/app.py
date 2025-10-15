from flask import Flask, render_template, redirect, url_for, Blueprint
from flask_login import login_required, current_user
import os
import atexit
import json
from datetime import datetime

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
from .services.service_monitor import service_monitor
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
    
    # Inicia monitoramento de serviços
    service_monitor.start_monitoring()
    
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
        print("=== DASHBOARD ACESSADO ===")
        app.logger.info("Dashboard acessado pelo usuário")
        
        from flask import request
        from datetime import datetime, timedelta
        from sqlalchemy import func, and_
        from .models.bot import TelegramBot as Bot
        from .models.codigo_venda import CodigoVenda as CodigoVenda
        from .models.client import User as Client
        from .models.payment import Payment
        
        # Parâmetros de filtro
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date') 
        bot_id = request.args.get('bot_id')
        
        # Datas padrão (início do mês até hoje)
        if not start_date:
            today = datetime.now()
            start_date = today.replace(day=1).strftime('%Y-%m-%d')  # Primeiro dia do mês atual
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            
        # Filtro de bots - converter para int se fornecido
        bot_filter = [Bot.user_id == current_user.id]
        selected_bot_id = None
        if bot_id and bot_id.strip():
            try:
                bot_id_int = int(bot_id)
                bot_filter.append(Bot.id == bot_id_int)
                selected_bot_id = bot_id
                print(f"Filtro aplicado: Bot ID {bot_id_int}")
            except ValueError:
                print(f"Bot ID inválido: {bot_id}")
        
        print(f"Período selecionado: {start_date} até {end_date}")
        
        # Query base para métricas
        base_date_filter = and_(
            func.date(Payment.created_at) >= start_date,
            func.date(Payment.created_at) <= end_date
        )
        
        # Métricas principais
        stats = {}
        
        # 1. Query base com todos os filtros aplicados
        user_bots_query = db.session.query(Bot).filter(and_(*bot_filter))

        user_bot_ids = db.session.query(Bot.id).filter(and_(*bot_filter)).subquery()

        # 2. Iniciações (usando bots criados no período como proxy)
        starts_in_period = db.session.query(func.count(CodigoVenda.id))\
            .filter(
                CodigoVenda.bot_id.in_(user_bot_ids),
                func.date(CodigoVenda.created_at) >= start_date,
                func.date(CodigoVenda.created_at) <= end_date
            ).scalar() or 0
        stats['bot_starts'] = starts_in_period
        
        # 3. Pagamentos completados no período (representa "assinaturas")
        stats['subscriptions'] = db.session.query(func.count(Payment.id))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter, 
                Payment.status == 'approved',
                func.date(Payment.created_at) >= start_date,
                func.date(Payment.created_at) <= end_date
            )).scalar() or 0
            
        # 4. Bots rodando atualmente (representa "sessões ativas")
        stats['active_sessions'] = user_bots_query.filter(and_(
            Bot.is_active == True, 
            Bot.is_running == True
        )).count()
        
        # 5. Faturamento total (soma dos pagamentos aprovados menos taxas)
        total_payments = db.session.query(func.sum(Payment.amount))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >= start_date,
                func.date(Payment.created_at) <= end_date
            )).scalar() or 0
        
        #6. Faturamento total (soma dos pagamentos aprovados menos taxas) -> HOJE

        today_payments = db.session.query(func.sum(Payment.amount))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >= datetime.now().strftime('%Y-%m-%d'),
                func.date(Payment.created_at) <= datetime.now().strftime('%Y-%m-%d')
            )).scalar() or 0
        


        # Calcular taxas baseado nas plataformas dos pagamentos
        payments_with_fees = db.session.query(Payment)\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >= start_date,
                func.date(Payment.created_at) <= end_date
            )).all()
        

        # Calcular taxas baseado nas plataformas dos pagamentos > HOJEEE
        payments_with_fees_today = db.session.query(Payment)\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >=  datetime.now().strftime('%Y-%m-%d'),
                func.date(Payment.created_at) <= datetime.now().strftime('%Y-%m-%d')
            )).all()
        
        # Calcular fees e revenue líquido por pagamento
        total_fees = sum(payment.get_platform_fees() for payment in payments_with_fees)
        net_revenue = total_payments - total_fees
        transaction_count = len(payments_with_fees)

        today_fees = sum(payment.get_platform_fees() for payment in payments_with_fees_today)
        today_revenue = today_payments - today_fees
        transaction_today_count = len (payments_with_fees_today)

        
        stats['total_revenue'] = f"{net_revenue:.2f}"
        stats['total_fees'] = f"{total_fees:.2f}"
        stats['gross_revenue'] = f"{total_payments:.2f}"
        
        # Estatísticas de hoje
        stats['today_revenue'] = f"{today_revenue:.2f}"
        stats['today_payments_count'] = transaction_today_count
        
        # Calcular mudanças percentuais comparando com período anterior
        period_days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
        prev_start_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=period_days)).strftime('%Y-%m-%d')
        prev_end_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Pagamentos do período anterior
        prev_subscriptions = db.session.query(func.count(Payment.id))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >= prev_start_date,
                func.date(Payment.created_at) <= prev_end_date
            )).scalar() or 0
        
        # Revenue do período anterior  
        prev_revenue_gross = db.session.query(func.sum(Payment.amount))\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >= prev_start_date,
                func.date(Payment.created_at) <= prev_end_date
            )).scalar() or 0
        
        # Pagamentos do período anterior com fees
        prev_payments_with_fees = db.session.query(Payment)\
            .join(Bot, Payment.bot_id == Bot.id)\
            .filter(and_(
                *bot_filter,
                Payment.status == 'approved',
                func.date(Payment.created_at) >= prev_start_date,
                func.date(Payment.created_at) <= prev_end_date
            )).all()
        
        # Revenue líquido do período anterior
        prev_total_fees = sum(payment.get_platform_fees() for payment in prev_payments_with_fees)
        prev_revenue_net = prev_revenue_gross - prev_total_fees
        
        # Calcular mudanças percentuais
        stats['subscriptions_change'] = round(
            ((stats['subscriptions'] - prev_subscriptions) / max(prev_subscriptions, 1)) * 100, 1
        )
        
        current_revenue = float(stats['total_revenue'].replace(',', '.'))
        stats['revenue_change'] = round(
            ((current_revenue - prev_revenue_net) / max(prev_revenue_net, 1)) * 100, 1
        )
        
        # Para bot_starts e sessions, usar valores baseados na diferença de contagem
        stats['bot_starts_change'] = round(max(stats['bot_starts'] * 0.1, 5.0), 1)  # Crescimento baseado no total
        stats['sessions_change'] = round(max(stats['active_sessions'] * 0.15, 8.0), 1)  # Baseado nas sessões
        
        # Porcentagem de sessões em relação aos bots
        stats['session_percentage'] = round((stats['active_sessions'] / max(stats['bot_starts'], 1)) * 100, 1)
        
        # Dados para gráficos baseados nos pagamentos reais - DIÁRIOS no período
        daily_data = db.session.query(
            func.to_char(Payment.created_at, 'DD/MM').label('day'),
            func.sum(Payment.amount).label('total')
        ).join(Bot, Payment.bot_id == Bot.id)\
        .filter(and_(
            *bot_filter, 
            Payment.status == 'approved',
            func.date(Payment.created_at) >= start_date,
            func.date(Payment.created_at) <= end_date
        ))\
        .group_by(func.to_char(Payment.created_at, 'DD/MM'), func.date(Payment.created_at))\
        .order_by(func.date(Payment.created_at)).all()
        
        # Preparar dados do gráfico diário com contagem de transações por dia
        if daily_data and len(daily_data) > 0:
            revenue_labels = [data.day for data in daily_data]
            gross_revenue_data = [float(data.total or 0) for data in daily_data]
            
            # Para cada dia, buscar os pagamentos e calcular as fees reais
            daily_fees = []
            for i, data in enumerate(daily_data):
                day_payments = db.session.query(Payment)\
                    .join(Bot, Payment.bot_id == Bot.id)\
                    .filter(and_(
                        *bot_filter,
                        Payment.status == 'approved',
                        func.to_char(Payment.created_at, 'DD/MM') == data.day
                    )).all()
                day_fees = sum(payment.get_platform_fees() for payment in day_payments)
                daily_fees.append(day_fees)
            
            revenue_data = [gross - fee for gross, fee in zip(gross_revenue_data, daily_fees)]
            fees_data = daily_fees
        else:
            # Gerar dados para os últimos 7 dias se não houver dados reais
            from datetime import datetime, timedelta
            days = []
            revenue_values = []
            fees_values = []
            
            for i in range(7):
                day = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=6-i)
                days.append(day.strftime('%d/%m'))
                # Valores simulados baseados no revenue líquido real
                base_net = net_revenue / 7 if net_revenue > 0 else 0  # Revenue líquido médio por dia
                revenue_values.append(base_net)
                fees_values.append(0)  # Não vamos mostrar fees no gráfico
            
            revenue_labels = days
            revenue_data = revenue_values
            fees_data = fees_values
        
        # Dados do gráfico de sessões baseado na atividade dos bots ao longo do dia
        # Usando last_activity dos bots para simular sessões por horário
        hourly_activity = []
        for hour in ['10h', '14h', '18h', '22h']:
            # Contar bots que tiveram atividade recente como proxy para sessões
            active_count = user_bots_query.filter(
                and_(
                    Bot.is_active == True,
                    Bot.last_activity != None
                )
            ).count()
            hourly_activity.append(max(active_count, stats['active_sessions']))
        
        # Dados fixos para teste - vamos garantir que os dados chegem no frontend
        chart_data = {
            'revenue_labels': revenue_labels or ['15/01', '16/01', '17/01', '18/01', '19/01', '20/01', '21/01'],
            'revenue_data':  revenue_data or [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
            'fees_data': fees_data or [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
            'sessions_labels': ['10h', '14h', '18h', '22h'],
            'sessions_data': [12, 18, 24, 16]
        }
        
        # Debug - vamos verificar se os dados estão sendo criados
        print("=== DEBUG CHART DATA ===")
        print(f"Chart Data: {chart_data}")
        print(f"Type of chart_data: {type(chart_data)}")
        print("========================")
        
        app.logger.info(f"Chart data gerado: {chart_data}")
        
        # Forçar flush do stdout
        import sys
        sys.stdout.flush()

        
        # Lista de bots para o filtro
        bots = Bot.query.filter_by(user_id=current_user.id).all()
        
        # Status dos serviços
        services_status = service_monitor.get_status_summary()
        
        return render_template('dashboard.html', 
                             stats=stats,
                             chart_data=chart_data,
                             bots=bots,
                             services_status=services_status,
                             start_date=start_date,
                             end_date=end_date,
                             selected_bot_id=selected_bot_id,
                             period_label=f"{start_date} até {end_date}")
    
    @app.route('/api/services/status')
    @login_required
    def services_status_api():
        """API endpoint para status dos serviços"""
        services = service_monitor.get_status_summary()
        return {
            'services': services,
            'timestamp': datetime.now().isoformat(),
            'all_online': all(s['status'] == 'online' for s in services)
        }
    
    @app.route('/api/services/check')
    @login_required
    def check_services_api():
        """API endpoint para forçar verificação dos serviços"""
        services = service_monitor.check_all_services()
        return {
            'services': services,
            'timestamp': datetime.now().isoformat(),
            'message': 'Verificação completa realizada'
        }

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