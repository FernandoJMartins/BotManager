from flask import Blueprint, request, jsonify
from ...models.bot import TelegramBot
from ...models.payment import Payment
from ...database.models import db
from ...services.pushinpay_service import PushinPayService
from ...utils.logger import logger
import json
import requests
import threading

webhook_bp = Blueprint('webhook', __name__, url_prefix='/webhook')

def send_utm_conversion(codigo_venda, payment):
    """
    Envia conversão para plataformas de marketing (Facebook, Google, etc.)
    baseado nos parâmetros UTM capturados
    """
    try:
        utm_data = codigo_venda.get_utm_data()
        
        # Prepara dados da conversão
        conversion_data = {
            'event_name': 'Purchase',
            'value': payment.amount,
            'currency': 'BRL',
            'payment_id': payment.id,
            'telegram_user_id': codigo_venda.telegram_user_id,
            'timestamp': payment.paid_at.isoformat() if payment.paid_at else None,
            **utm_data  # Adiciona todos os dados UTM
        }
        
        logger.info(f"📊 Enviando conversão UTM: {json.dumps(conversion_data, indent=2)}")
        
        # Aqui você pode implementar envios para diferentes plataformas
        # baseado no utm_source
        
        if utm_data.get('utm_source') == 'fb':
            send_facebook_conversion(conversion_data)
        elif utm_data.get('utm_source') == 'google':
            send_google_conversion(conversion_data)
        else:
            # Log genérico para outras fontes
            logger.info(f"✅ Conversão registrada para {utm_data.get('utm_source', 'unknown')}: R$ {payment.amount}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar conversão UTM: {e}")

def send_facebook_conversion(conversion_data):
    """Envia conversão para Facebook Ads"""
    try:
        # Exemplo de integração com Facebook Conversions API
        # Você precisará configurar o FB_ACCESS_TOKEN e FB_PIXEL_ID
        
        logger.info(f"📘 Enviando conversão para Facebook: {conversion_data['utm_campaign']}")
        
        # TODO: Implementar Facebook Conversions API
        # fb_url = f"https://graph.facebook.com/v18.0/{FB_PIXEL_ID}/events"
        # headers = {
        #     'Authorization': f'Bearer {FB_ACCESS_TOKEN}',
        #     'Content-Type': 'application/json'
        # }
        # 
        # fb_data = {
        #     'data': [{
        #         'event_name': 'Purchase',
        #         'event_time': int(datetime.now().timestamp()),
        #         'user_data': {
        #             'client_ip_address': conversion_data.get('ip'),
        #             'external_id': str(conversion_data['telegram_user_id'])
        #         },
        #         'custom_data': {
        #             'currency': 'BRL',
        #             'value': conversion_data['value']
        #         }
        #     }]
        # }
        # 
        # response = requests.post(fb_url, headers=headers, json=fb_data)
        # logger.info(f"Facebook response: {response.status_code}")
        
        logger.info("✅ Conversão Facebook simulada (implemente a API real)")
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar para Facebook: {e}")

def send_google_conversion(conversion_data):
    """Envia conversão para Google Ads"""
    try:
        logger.info(f"🔍 Enviando conversão para Google: {conversion_data['utm_campaign']}")
        
        # TODO: Implementar Google Ads Conversions API
        # Você precisará configurar o GOOGLE_CONVERSION_ID e GOOGLE_CONVERSION_LABEL
        
        logger.info("✅ Conversão Google simulada (implemente a API real)")
        
    except Exception as e:
        logger.error(f"❌ Erro ao enviar para Google: {e}")

@webhook_bp.route('/pushinpay', methods=['POST'])
def pushinpay_webhook():
    """
    Webhook para receber confirmações de pagamento da PushinPay dos clientes finais
    """
    try:
        # Log das informações da requisição para debug
        logger.info(f"🔍 Webhook PushinPay - Content-Type: {request.content_type}")
        logger.info(f"🔍 Webhook PushinPay - Headers: {dict(request.headers)}")
        logger.info(f"🔍 Webhook PushinPay - Raw Data: {request.get_data()}")
        
        # PushinPay envia dados como application/x-www-form-urlencoded
        if request.content_type == 'application/x-www-form-urlencoded':
            # Processa dados do formulário
            data = request.form.to_dict()
            logger.info(f"📋 Dados do formulário processados: {json.dumps(data, indent=2)}")
        else:
            # Tenta pegar os dados como JSON (fallback)
            try:
                data = request.get_json(force=True)
                logger.info(f"📄 Dados JSON processados: {json.dumps(data, indent=2)}")
            except Exception as json_error:
                logger.error(f"❌ Erro ao parsear JSON: {json_error}")
                # Último recurso: tenta extrair dados do texto bruto
                raw_data = request.get_data(as_text=True)
                logger.info(f"📄 Dados como texto: {raw_data}")
                return jsonify({'error': 'Formato de dados inválido', 'details': str(json_error)}), 400
        
        if not data:
            logger.error("❌ Dados vazios recebidos")
            return jsonify({'error': 'Dados inválidos'}), 400
        
        # Log do webhook recebido
        logger.info(f"✅ Webhook PushinPay recebido: {json.dumps(data, indent=2)}")
        
        # Extrai informações importantes
        transaction_id = data.get('id')  # ID da transação na PushinPay
        status = data.get('status')      # Status do pagamento
        
        if not transaction_id:
            logger.error(f"ID da transação ausente: {data}")
            return jsonify({'error': 'ID da transação ausente'}), 400
        
        # Converte transaction_id para lowercase para bater com o formato do banco
        transaction_id_lower = transaction_id.lower()
        logger.info(f"🔍 Buscando pagamento com pix_code: {transaction_id_lower}")
        
        # Busca o pagamento na nossa base pelo pix_code
        payment = Payment.query.filter_by(pix_code=transaction_id_lower).first()
        
        if not payment:
            logger.error(f"Pagamento não encontrado para ID: {transaction_id}")
            return jsonify({'error': 'Pagamento não encontrado'}), 404
        
        # Atualiza status do pagamento baseado no webhook
        old_status = payment.status
        
        if status in ['approved', 'paid', 'completed', 'success']:
            # Extrai informações do pagador do webhook da PushinPay
            payer_name = data.get('payer_name')
            payer_cpf = data.get('payer_national_registration')
            
            if payer_name:
                payment.payer_name = payer_name.replace('+', ' ')  # Decodifica URL encoding
                logger.info(f"📋 Nome do pagador capturado: {payment.payer_name}")
            
            if payer_cpf:
                payment.payer_cpf = payer_cpf
                logger.info(f"📋 CPF do pagador capturado: {payment.payer_cpf}")
            
            payment.process_payment()  # Marca como completed e paid_at
            
            # Envia UTMs se existir código de venda associado
            try:
                from ...models.codigo_venda import CodigoVenda
                codigo_venda = CodigoVenda.query.filter_by(payment_id=payment.id).first()
                if codigo_venda:
                    send_utm_conversion(codigo_venda, payment)
            except Exception as utm_error:
                logger.error(f"Erro ao enviar UTMs: {utm_error}")
            
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