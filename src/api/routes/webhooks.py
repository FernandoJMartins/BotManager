from flask import Blueprint, request, jsonify
from ...models.bot import TelegramBot
from ...models.payment import Payment
from ...database.models import db
from ...services.pushinpay_service import PushinPayService
from ...utils.logger import logger
import json

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

@webhook_bp.route('/pushinpay', methods=['POST'])
def pushinpay_webhook():
    """
    Webhook para receber confirmações de pagamento da PushinPay
    """
    try:
        # Pega os dados do webhook
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados inválidos'}), 400
        
        # Log do webhook recebido
        logger.info(f"Webhook PushinPay recebido: {json.dumps(data, indent=2)}")
        
        # Extrai informações importantes
        transaction_id = data.get('id')  # ID da transação na PushinPay
        status = data.get('status')      # Status do pagamento
        reference = data.get('reference')  # Nossa referência (bot_id)
        
        if not all([transaction_id, status, reference]):
            logger.error(f"Dados obrigatórios ausentes: {data}")
            return jsonify({'error': 'Dados obrigatórios ausentes'}), 400
        
        # Busca o pagamento na nossa base
        payment = Payment.query.filter_by(
            external_payment_id=transaction_id
        ).first()
        
        if not payment:
            # Tenta buscar por referência (bot_id)
            try:
                bot_id = int(reference)
                bot = TelegramBot.query.get(bot_id)
                if bot:
                    # Cria um novo registro de pagamento se não existir
                    payment = Payment(
                        user_id=bot.user_id,
                        bot_id=bot_id,
                        amount=0.70,  # Taxa fixa
                        external_payment_id=transaction_id,
                        payment_method='pix',
                        status='pending'
                    )
                    db.session.add(payment)
            except ValueError:
                logger.error(f"Referência inválida: {reference}")
                return jsonify({'error': 'Referência inválida'}), 400
        
        if not payment:
            logger.error(f"Pagamento não encontrado para transação: {transaction_id}")
            return jsonify({'error': 'Pagamento não encontrado'}), 404
        
        # Atualiza status do pagamento baseado no webhook
        old_status = payment.status
        
        if status == 'approved' or status == 'paid':
            payment.status = 'completed'
            payment.paid_at = db.func.now()
            
            # Ativa o bot automaticamente
            if payment.bot_id:
                bot = TelegramBot.query.get(payment.bot_id)
                if bot:
                    bot.is_active = True
                    bot.payment_status = 'paid'
                    logger.info(f"Bot {bot.id} ativado automaticamente após pagamento")
                    
        elif status == 'cancelled' or status == 'failed':
            payment.status = 'failed'
            
            # Desativa o bot se necessário
            if payment.bot_id:
                bot = TelegramBot.query.get(payment.bot_id)
                if bot:
                    bot.is_active = False
                    bot.payment_status = 'failed'
                    logger.info(f"Bot {bot.id} desativado devido a falha no pagamento")
        
        # Salva as alterações
        db.session.commit()
        
        logger.info(f"Pagamento {payment.id} atualizado de '{old_status}' para '{payment.status}'")
        
        return jsonify({
            'message': 'Webhook processado com sucesso',
            'payment_id': payment.id,
            'status': payment.status
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao processar webhook PushinPay: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@webhook_bp.route('/test', methods=['GET'])
def test_webhook():
    """Endpoint de teste para verificar se os webhooks estão funcionando"""
    return jsonify({
        'message': 'Webhook endpoint funcionando',
        'timestamp': db.func.now()
    }), 200