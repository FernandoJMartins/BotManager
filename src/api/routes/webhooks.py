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
    Webhook para receber confirmações de pagamento da PushinPay dos clientes finais
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
        
        if not transaction_id:
            logger.error(f"ID da transação ausente: {data}")
            return jsonify({'error': 'ID da transação ausente'}), 400
        
        # Busca o pagamento na nossa base pelo pix_code
        payment = Payment.query.filter_by(pix_code=transaction_id).first()
        
        if not payment:
            logger.error(f"Pagamento não encontrado para ID: {transaction_id}")
            return jsonify({'error': 'Pagamento não encontrado'}), 404
        
        # Atualiza status do pagamento baseado no webhook
        old_status = payment.status
        
        if status in ['approved', 'paid', 'completed', 'success']:
            payment.process_payment()  # Marca como completed e paid_at
            
            # Notifica o cliente via bot Telegram
            if payment.telegram_user_id and payment.bot:
                try:
                    from ...services.telegram_bot_manager import bot_manager
                    
                    # Envia notificação de pagamento confirmado
                    bot_token = payment.bot.bot_token
                    if bot_token in bot_manager.active_bots:
                        application = bot_manager.active_bots[bot_token]
                        
                        # Envia mensagem de confirmação
                        import asyncio
                        def send_confirmation():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                application.bot.send_message(
                                    chat_id=payment.telegram_user_id,
                                    text=f"✅ Pagamento de R$ {payment.amount:.2f} confirmado!\n\nObrigado pela sua compra!"
                                )
                            )
                        
                        import threading
                        threading.Thread(target=send_confirmation, daemon=True).start()
                        
                except Exception as e:
                    logger.error(f"Erro ao notificar cliente: {e}")
                    
            logger.info(f"Pagamento {payment.pix_code} confirmado - R$ {payment.amount:.2f}")
                    
        elif status in ['cancelled', 'failed', 'expired']:
            payment.status = 'failed'
            logger.info(f"Pagamento {payment.pix_code} cancelado/falhado")
        
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