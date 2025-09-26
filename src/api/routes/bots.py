from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from ...models.bot import TelegramBot
from ...models.payment import Payment
from ...database.models import db
from ...services.telegram_validation import TelegramValidationService
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
            'is_paid': bot.is_paid,
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
        
        token = data.get('token')
        welcome_message = data.get('welcome_message', '')
        pix_values = data.get('pix_values', '[]')  # JSON string
        
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
                bot_name=validation_result['first_name'],
                welcome_message=welcome_message,
                welcome_image=welcome_image_path,
                welcome_audio=welcome_audio_path,
                pix_values=pix_values,
                user_id=current_user.id,
                is_active=False,  # Será ativado após pagamento
                is_paid=False
            )
            
            db.session.add(bot)
            db.session.flush()  # Para obter o ID do bot
            
            # Verifica se usuário tem token PushinPay
            if not current_user.pushinpay_token:
                flash('Configure seu token PushinPay no perfil antes de criar bots.', 'error')
                return redirect(url_for('auth.profile'))
            
            # Gera pagamento PIX
            pix_service = PushinPayService()
            pix_data = pix_service.create_pix_payment(
                user_pushinpay_token=current_user.pushinpay_token,
                user_id=current_user.id,
                bot_id=bot.id,
                description=f"Ativacao Bot {validation_result['username']}"
            )
            
            # Verifica se o PIX foi gerado com sucesso
            if not pix_data.get('success'):
                flash(f'Erro ao gerar PIX: {pix_data.get("error", "Erro desconhecido")}', 'error')
                return render_template('bots/create.html')
            
            # Cria registro de pagamento
            payment = Payment(
                pix_code=pix_data.get('pix_code', str(bot.id)),
                amount=float(pix_data.get('amount', 0.70)),
                pix_key=pix_data.get('pix_copy_paste', ''),
                pix_qr_code=pix_data.get('qr_code', ''),
                expires_at=pix_data.get('expires_at'),
                user_id=current_user.id,
                bot_id=bot.id
            )
            
            db.session.add(payment)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'bot_id': bot.id,
                    'payment': {
                        'pix_code': pix_data['pix_code'],
                        'amount': pix_data['amount'],
                        'qr_code': pix_data['qr_code'],
                        'pix_copy_paste': pix_data['pix_copy_paste'],
                        'expires_at': pix_data['expires_at'].isoformat()
                    },
                    'message': 'Bot criado! Realize o pagamento para ativá-lo.'
                }), 201
            
            flash('Bot criado com sucesso! Realize o pagamento para ativá-lo.', 'success')
            return redirect(url_for('bots.payment_status', bot_id=bot.id))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': f'Erro ao criar bot: {str(e)}'}), 500
            flash(f'Erro ao criar bot: {str(e)}', 'error')
            return render_template('bots/create.html')
    
    return render_template('bots/create.html')


@bots_bp.route('/payment/<int:bot_id>', methods=['GET'])
@login_required
def payment_status(bot_id):
    """Exibe status do pagamento do bot"""
    bot = TelegramBot.query.filter_by(id=bot_id, user_id=current_user.id).first()
    if not bot:
        flash('Bot não encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Busca pagamento pendente
    payment = Payment.query.filter_by(bot_id=bot_id).filter(Payment.status == 'pending').first()
    if not payment:
        flash('Pagamento não encontrado.', 'error')
        return redirect(url_for('dashboard.index'))
    
    return render_template('bots/payment.html', bot=bot, payment=payment)


@bots_bp.route('/api/payments/check/<int:bot_id>', methods=['GET'])
@login_required
def check_payment_status_api(bot_id):
    """API para verificar status do pagamento"""
    bot = TelegramBot.query.filter_by(id=bot_id, user_id=current_user.id).first()
    if not bot:
        return jsonify({'error': 'Bot não encontrado'}), 404
    
    # Verifica se bot já está pago
    if bot.is_paid:
        return jsonify({'paid': True, 'status': 'confirmed'})
    
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
                bot.is_paid = True
                bot.is_active = True
                db.session.commit()
                
                return jsonify({'paid': True, 'status': 'confirmed'})
                
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento: {e}")
    
    return jsonify({'paid': False, 'status': 'pending'})