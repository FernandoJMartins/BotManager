from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from ...models.bot import TelegramBot
from ...models.payment import Payment
from ...database.models import db
from ...services.pushinpay_service import PushinPayService
from ...utils.logger import logger

bots_bp = Blueprint('bots', __name__, url_prefix='/bots')

# Configurações de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bots_bp.route('/', methods=['GET'])
@login_required
def list_bots():
    """Lista todos os bots do usuário"""
    user_bots = TelegramBot.query.filter_by(user_id=current_user.id).all()
    
    bots_data = []
    for bot in user_bots:
        bots_data.append({
            'id': bot.id,
            'username': bot.bot_username,
            'name': bot.bot_name,
            'status': bot.get_status(),
            'is_active': bot.is_active,
            'is_running': bot.is_running,
            'created_at': bot.created_at.isoformat() if bot.created_at else None
        })
    
    if request.is_json:
        return jsonify({
            'bots': bots_data,
            'total': len(bots_data),
            'can_add_more': current_user.can_add_bot()
        })
    
    return render_template('bots/list.html', bots=bots_data, can_add_more=current_user.can_add_bot())

@bots_bp.route('/validate-token', methods=['POST'])
@login_required
def validate_token():
    """Valida token do bot do Telegram"""
    data = request.get_json() if request.is_json else request.form
    token = data.get('token')
    
    if not token:
        return jsonify({'error': 'Token é obrigatório'}), 400
    
    # Verifica se usuário pode adicionar mais bots
    if not current_user.can_add_bot():
        return jsonify({'error': 'Limite de 30 bots atingido'}), 400
    
    # Verifica se token já está em uso
    existing_bot = TelegramBot.query.filter_by(bot_token=token).first()
    if existing_bot:
        return jsonify({'error': 'Token já está sendo usado por outro bot'}), 400
    
    # Valida token com API do Telegram
    validation_service = TelegramValidationService()
    validation_result = validation_service.validate_bot_token(token)
    
    if not validation_result['valid']:
        return jsonify({'error': validation_result['error']}), 400
    
    return jsonify({
        'valid': True,
        'bot_info': validation_result,
        'message': 'Token válido! Agora configure seu bot.'
    })

@bots_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_bot():
    """Cria um novo bot"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        token = data.get('token', '').strip()
        name = data.get('name', '').strip()
        welcome_message = data.get('welcome_message', '').strip() or "Olá! Bem-vindo ao meu bot!"
        
        # Processa valores PIX
        pix_values_raw = request.form.getlist('pix_values[]') if not request.is_json else data.get('pix_values', [])
        pix_values = []
        for value in pix_values_raw:
            if value and float(value) > 0:
                pix_values.append(float(value))
        
        # Se não tem valores, usa padrões
        if not pix_values:
            pix_values = [10.0, 20.0, 50.0]
        
        import json
        pix_values_json = json.dumps(pix_values)
        
        if not token:
            if request.is_json:
                return jsonify({'error': 'Token é obrigatório'}), 400
            flash('Token é obrigatório', 'error')
            return render_template('bots/create.html')
        
        # Verifica limite de bots
        if not current_user.can_add_bot():
            if request.is_json:
                return jsonify({'error': 'Limite de 30 bots atingido'}), 400
            flash('Você atingiu o limite de 30 bots', 'error')
            return redirect(url_for('bots.list_bots'))
        
        # Verifica se o token já está sendo usado
        existing_bot = TelegramBot.query.filter_by(bot_token=token).first()
        if existing_bot:
            if request.is_json:
                return jsonify({'error': 'Este token já está sendo usado por outro bot'}), 400
            flash('Este token já está sendo usado por outro bot', 'error')
            return render_template('bots/create.html')
        
        # Valida token novamente
        validation_service = TelegramValidationService()
        validation_result = validation_service.validate_bot_token(token)
        
        if not validation_result['valid']:
            if request.is_json:
                return jsonify({'error': validation_result['error']}), 400
            flash(f'Token inválido: {validation_result["error"]}', 'error')
            return render_template('bots/create.html')
        
        try:
            # Processa uploads de arquivos
            welcome_image_path = None
            welcome_audio_path = None
            
            if 'welcome_image' in request.files:
                file = request.files['welcome_image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    welcome_image_path = os.path.join(UPLOAD_FOLDER, 'images', filename)
                    os.makedirs(os.path.dirname(welcome_image_path), exist_ok=True)
                    file.save(welcome_image_path)
            
            if 'welcome_audio' in request.files:
                file = request.files['welcome_audio']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    welcome_audio_path = os.path.join(UPLOAD_FOLDER, 'audio', filename)
                    os.makedirs(os.path.dirname(welcome_audio_path), exist_ok=True)
                    file.save(welcome_audio_path)
            
            # Cria o bot
            bot = TelegramBot(
                bot_token=token,
                bot_username=validation_result['username'],
                bot_name=name or validation_result['first_name'],
                welcome_message=welcome_message,
                pix_values=pix_values_json,
                user_id=current_user.id,
                is_active=True  # Ativo imediatamente
            )
            
            db.session.add(bot)
            db.session.flush()  # Para obter o ID do bot
            
            # Verifica se usuário tem token PushinPay
            if not current_user.pushinpay_token:
                flash('Configure seu token PushinPay no perfil antes de criar bots.', 'error')
                return redirect(url_for('auth.profile'))
            
            # Bot é criado diretamente ativo (sem necessidade de pagamento interno)
            bot.is_active = True
            db.session.commit()
            
            # Inicia o bot Telegram automaticamente
            from ...services.telegram_bot_manager import bot_manager
            import asyncio
            
            def start_bot_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_manager.start_bot(bot))
            
            import threading
            bot_thread = threading.Thread(target=start_bot_async, daemon=True)
            bot_thread.start()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'bot_id': bot.id,
                    'message': 'Bot criado e ativado com sucesso!'
                }), 201
            
            flash('Bot criado e ativado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': f'Erro ao criar bot: {str(e)}'}), 500
            flash(f'Erro ao criar bot: {str(e)}', 'error')
            return render_template('bots/create_new.html')
    
    return render_template('bots/create_new.html')


@bots_bp.route('/payment/<int:bot_id>', methods=['GET'])
@login_required
def payment_status(bot_id):
    """Exibe status do pagamento do bot"""
    bot = TelegramBot.query.filter_by(id=bot_id, user_id=current_user.id).first()
    if not bot:
        flash('Bot não encontrado.', 'error')
        return redirect(url_for('dashboard'))
    
    # Busca pagamento pendente
    payment = Payment.query.filter_by(bot_id=bot_id).filter(Payment.status == 'pending').first()
    if not payment:
        flash('Pagamento não encontrado.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('bots/payment.html', bot=bot, payment=payment)


@bots_bp.route('/api/payments/check/<int:bot_id>', methods=['GET'])
@login_required
def check_payment_status_api(bot_id):
    """API para verificar status do pagamento"""
    bot = TelegramBot.query.filter_by(id=bot_id, user_id=current_user.id).first()
    if not bot:
        return jsonify({'error': 'Bot não encontrado'}), 404
    
    # Busca pagamento pendente
    payment = Payment.query.filter_by(bot_id=bot_id).filter(Payment.status == 'pending').first()
    if not payment:
        return jsonify({'paid': False, 'status': 'no_payment'})
    
    # Verifica com a PushinPay se necessário
    if current_user.pushinpay_token:
        pix_service = PushinPayService()
        try:
            status_result = pix_service.check_payment_status(
                current_user.pushinpay_token,
                payment.pix_code
            )
            
            if status_result.get('paid'):
                # Confirma pagamento localmente
                payment.status = 'completed'
                payment.paid_at = datetime.utcnow()
                bot.is_active = True
                db.session.commit()
                
                return jsonify({'paid': True, 'status': 'confirmed'})
                
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento: {e}")
    
        return jsonify({'paid': False, 'status': 'pending'})

@bots_bp.route('/edit/<slug>', methods=['GET', 'POST'])
@login_required
def edit_bot(slug):
    """Edita um bot através da slug única"""
    # Busca o bot pela slug (que é o ID do bot)
    try:
        bot_id = int(slug)
        bot = TelegramBot.query.get_or_404(bot_id)
    except ValueError:
        flash('Bot não encontrado.', 'error')
        return redirect(url_for('bots.list_bots'))
    
    # Verifica se o usuário tem permissão (dono do bot ou admin)
    if bot.user_id != current_user.id and not current_user.is_admin:
        flash('Você não tem permissão para editar este bot.', 'error')
        return redirect(url_for('bots.list_bots'))
    
    if request.method == 'POST':
        try:
            # Atualiza informações básicas
            bot.bot_name = request.form.get('name', '').strip()
            bot.bot_token = request.form.get('token', '').strip()
            bot.welcome_message = request.form.get('welcome_message', '').strip()
            
            # Atualiza valores PIX e nomes dos planos
            pix_values = []
            plan_names = []
            
            for value in request.form.getlist('pix_values[]'):
                if value and float(value) > 0:
                    pix_values.append(float(value))
            
            for name in request.form.getlist('plan_names[]'):
                if name and name.strip():
                    plan_names.append(name.strip())
            
            bot.pix_values = pix_values
            bot.plan_names = plan_names
            
            # Atualiza IDs dos grupos
            id_vip = request.form.get('id_vip', '').strip()
            id_logs = request.form.get('id_logs', '').strip()
            
            if id_vip:
                # Remove @ ou qualquer prefixo e mantém apenas números e -
                id_vip = id_vip.replace('@', '').replace('https://t.me/', '')
                if not id_vip.startswith('-'):
                    id_vip = '-' + id_vip
                bot.id_vip = id_vip
            else:
                bot.id_vip = None
                
            if id_logs:
                # Remove @ ou qualquer prefixo e mantém apenas números e -
                id_logs = id_logs.replace('@', '').replace('https://t.me/', '')
                if not id_logs.startswith('-'):
                    id_logs = '-' + id_logs
                bot.id_logs = id_logs
            else:
                bot.id_logs = None
            
            # Processa upload de imagem de boas-vindas
            if 'welcome_image' in request.files:
                file = request.files['welcome_image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"bot_{bot.id}_welcome_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    bot.welcome_image = file_path
            
            # Processa upload de áudio de boas-vindas
            if 'welcome_audio' in request.files:
                file = request.files['welcome_audio']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filename = f"bot_{bot.id}_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    bot.welcome_audio = file_path
            
            db.session.commit()
            
            flash('Bot atualizado com sucesso!', 'success')
            logger.info(f"Bot {bot.bot_name} (ID: {bot.id}) atualizado pelo usuário {current_user.email}")
            
            return redirect(url_for('bots.edit_bot', slug=slug))
            
        except Exception as e:
            logger.error(f"Erro ao atualizar bot: {e}")
            flash('Erro ao atualizar bot. Tente novamente.', 'error')
            db.session.rollback()
    
    return render_template('bots/edit.html', bot=bot)


# Rota para iniciar bot