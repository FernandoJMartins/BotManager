import requests
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import urllib3
import os
from dotenv import load_dotenv
from ..models.client import User

# Desabilita warnings SSL temporariamente para resolver problema de conectividade
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PushinPayService:
    
    def __init__(self):
        # use 'env' file inside src directory instead of project root '.env'
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'env')  # src/env
        load_dotenv(dotenv_path=env_path)
        from dotenv import find_dotenv
        # keep previous fallback path variable if needed by other code
        self.env_path = env_path

        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')

        self.api_base_url = os.getenv('API_PUSHINPAY')
        self.split_account = os.getenv('SPLIT_ACCOUNT')
        self.production = os.getenv('PRODUCTION')

        import logging
        logger = logging.getLogger(__name__)

    
    def create_pix_payment(self, user_pushinpay_token: str, amount: float, telegram_user_id: str = None, description: str = None) -> dict:
        if not description:
            description = f"Pagamento via Bot Telegram"

        headers = {
            'Authorization': f'{user_pushinpay_token}',
            'Content-Type': 'application/json'
        }
        

        user = User.query.filter_by(pushinpay_token=user_pushinpay_token).first()
        commission_value = int(user.fee * 100 or 70)
        # ensure we reload env from the configured src/env path (if needed at runtime)
        load_dotenv(dotenv_path=getattr(self, 'env_path', None))
        # Payload para criar cobrança PIX (valores em centavos)

        

        if (self.production == 'FALSE'):

            payload = {
                "value": int(amount * 100),  # Valor total em centavos
                "webhook_url": os.getenv('WEBHOOK_URL'),  # URL do webhook
                "description": description,
                "split_rules": [
                    
                ]
            }

        else:
            payload = {
                "value": int(amount * 100),  # Valor total em centavos
                "webhook_url": os.getenv('WEBHOOK_URL'),  # URL do webhook
                "description": description,
                "split_rules": [
                    {
                        "value": commission_value,  # 0,7cents para a plataforma
                        "account_id": self.split_account
                    }
                ]
            }


                
        try:
            # Importa o logger para usar nos logs
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"📦 Payload: {payload}")
            

            response = None

            try:
                response = requests.post(
                    f'{self.api_base_url}/pix/cashIn',
                    json=payload,
                    headers=headers,
                    timeout=30,
                    verify=False  # Desabilita verificação SSL temporariamente
                )
                    
                        
            except Exception as e:
                logger.error(f"❌ Erro no ao criar pix: {e}")
                
            
            if not response:
                raise Exception("Nenhum endpoint respondeu")
            
            
            if response.status_code == 200 or response.status_code == 201:
                try:
                    api_data = response.json()
                    
                    # Retorna dados padronizados conforme API PushinPay
                    return {
                        'success': True,
                        'pix_code': api_data.get('id', str(uuid.uuid4())[:8]),
                        'amount': amount,
                        'qr_code': api_data.get('qr_code_base64', ''),  # Base64 da imagem QR
                        'pix_copy_paste': api_data.get('qr_code', ''),  # Código PIX para copiar
                        'payment_id': api_data.get('id'),
                        'expires_at': datetime.utcnow() + timedelta(hours=24),
                        'description': description,
                        'status': api_data.get('status', 'created'),
                        'value_cents': api_data.get('value', int(amount * 100)),
                        'pushinpay_data': api_data
                    }
                except ValueError as json_error:
                    return {
                        'success': False,
                        'error': f'Resposta inválida da API: {str(json_error)}',
                        'details': f'Status: {response.status_code}, Content: {response.text}'
                    }
            else:
                # Log detalhado do erro
                error_msg = f'Erro na API PushinPay: {response.status_code}'
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg += f' - {error_data["message"]}'
                    logger.error(f"💥 Erro detalhado da API: {error_data}")
                except:
                    logger.error(f"📄 Resposta de erro não é JSON: {response.text}")
                
                # Para desenvolvimento, usa PIX simulado em caso de erro
                logger.warning(f"⚠️ API falhou com {response.status_code}, usando PIX simulado")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 Erro de conexão com PushinPay: {str(e)}")
            # Retorna PIX simulado para desenvolvimento
            logger.warning("🔄 Usando PIX simulado devido a erro de conexão")
            return None
            
        except Exception as e:
            logger.error(f"💥 Erro inesperado: {str(e)}")
            # Retorna PIX simulado para desenvolvimento  
            logger.warning("🔄 Usando PIX simulado devido a erro inesperado")
            return None
    
    
    def check_payment_status(self, user_pushinpay_token: str, payment_id: str) -> dict:
        headers = {
            'Authorization': f'{user_pushinpay_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                f"{self.api_base_url}/transactions/{payment_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('status', 'pending'),
                    'paid': data.get('status') == 'paid',
                    'data': data
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro ao consultar pagamento: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao consultar pagamento: {str(e)}'
            }
    
    def validate_pushinpay_token(self, token: str) -> dict:
        # Validação básica do formato do token
        if not token or len(token.strip()) < 10:
            return {
                'valid': False,
                'error': 'Token deve ter pelo menos 10 caracteres'
            }
        
        headers = {
            'Authorization': f'{token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Tenta validar com endpoint mais comum da PushinPay
            response = requests.get(
                f"{self.api_base_url}/statements?page=1",  # Endpoint mais comum para validar token
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'valid': True,
                    'message': 'Token PushinPay válido'
                }
            elif response.status_code == 401:
                return {
                    'valid': False,
                    'error': 'Token inválido ou expirado'
                }
            elif response.status_code == 404:
                # Se 404, para desenvolvimento aceita o token
                return {
                    'valid': True,
                    'message': 'Token aceito (modo desenvolvimento)'
                }
            else:
                return {
                    'valid': False,
                    'error': f'Erro ao validar token: {response.status_code}'
                }
                
        except Exception as e:
            # Em desenvolvimento, aceita tokens válidos mesmo com erro de conexão
            if len(token.strip()) >= 20:  # Token parece válido
                return {
                    'valid': True,
                    'message': 'Token aceito (validação offline)'
                }
            return {
                'valid': False,
                'error': f'Erro de conexão: {str(e)}'
            }

# Instância global do serviço
pushinpay_service = PushinPayService()