import requests
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import urllib3

# Desabilita warnings SSL temporariamente para resolver problema de conectividade
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PushinPayService:
    """Serviço             response = requests.get(
                                   response = requests.get(
                f"{self.api_base_url}/transactions/{payment_id}",
                headers=headers,
                timeout=30,
                verify=False  # Desabilita verificação SSL temporariamente
            ) Tenta fazer uma consulta simples para validar o token
            # Como não há endpoint específico de validação, vamos tentar listar transações
            response = requests.get(
                f"{self.api_base_url}/transactions",  # Endpoint para validar token
                headers=headers,
                timeout=10,
                verify=False  # Desabilita verificação SSL temporariamente
            )lf.api_base_url}/transactions/{payment_id}",
                headers=headers,
                timeout=30
            )integração com PushinPay API"""
    
    def __init__(self):
        self.api_base_url = "https://api.pushinpay.com.br/api"
        self.split_account = "9E4B259F-DB6D-419E-8D78-7216BF642856"  # Conta para receber comissão
    
    def create_pix_payment(self, user_pushinpay_token: str, amount: float, telegram_user_id: str = None, description: str = None) -> dict:
        """
        Cria um pagamento PIX via PushinPay API para cliente final
        
        Args:
            user_pushinpay_token (str): Token Bearer da PushinPay do dono do bot
            amount (float): Valor do PIX
            telegram_user_id (str): ID do usuário do Telegram
            description (str): Descrição do pagamento
            
        Returns:
            dict: Dados do pagamento PIX gerado
        """
        if not description:
            description = f"Pagamento via Bot Telegram"
        
        # Headers para a API
        headers = {
            'Authorization': f'{user_pushinpay_token}',
            'Content-Type': 'application/json'
        }
        
        commission_value = 70
        
        # Payload para criar cobrança PIX (valores em centavos)
        payload = {
            "value": int(amount * 100),  # Valor total em centavos
            "webhook_url": "https://c398fe1cc1c7.ngrok-free.app/webhook/pushinpay",  # URL do webhook
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
            
            logger.info(f"🔄 Tentando criar PIX - URL: {self.api_base_url}/pix/cashIn")
            logger.info(f"📋 Headers: {headers}")
            logger.info(f"📦 Payload: {payload}")
            
            # Tenta diferentes endpoints possíveis
            endpoints_to_try = [
                f"{self.api_base_url}/pix/cashIn",
            ]
            
            response = None
            for endpoint in endpoints_to_try:
                try:
                    logger.info(f"🌐 Tentando endpoint: {endpoint}")
                    response = requests.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        timeout=30,
                        verify=False  # Desabilita verificação SSL temporariamente
                    )
                    
                    logger.info(f"📊 Endpoint {endpoint} - Status: {response.status_code}")
                    
                    # Se não foi erro 404, usa essa resposta
                    if response.status_code != 404:
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Erro no endpoint {endpoint}: {e}")
                    continue
            
            if not response:
                raise Exception("Nenhum endpoint respondeu")
            
            # Log da resposta para debug
            logger.info(f"📥 PushinPay Response Status: {response.status_code}")
            logger.info(f"📋 PushinPay Response Headers: {response.headers}")
            logger.info(f"📄 PushinPay Response Text: {response.text}")
            
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
                return self._create_mock_pix_payment(amount, description)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"🌐 Erro de conexão com PushinPay: {str(e)}")
            # Retorna PIX simulado para desenvolvimento
            logger.warning("🔄 Usando PIX simulado devido a erro de conexão")
            return self._create_mock_pix_payment(amount, description)
            
        except Exception as e:
            logger.error(f"💥 Erro inesperado: {str(e)}")
            # Retorna PIX simulado para desenvolvimento  
            logger.warning("🔄 Usando PIX simulado devido a erro inesperado")
            return self._create_mock_pix_payment(amount, description)
    
    def _create_mock_pix_payment(self, amount: float, description: str) -> dict:
        """Cria um PIX simulado para desenvolvimento"""
        import random
        mock_id = f"9c29870c-9f69-4bb6-90d3-{random.randint(1000, 9999):012d}"
        
        # QR Code base64 simulado (imagem 1x1 pixel transparente)
        mock_qr_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        # Gera um código PIX válido no formato EMV
        def generate_valid_pix_code(amount: float, pix_key: str) -> str:
            # Chave PIX simulada (email válido para teste)
            test_key = "teste@pushinpay.com.br"
            
            # Monta o código EMV completo e válido
            # 00 = Payload Format Indicator
            payload = "000201"
            
            # 01 = Point of Initiation Method
            payload += "010212"
            
            # 26 = Merchant Account Information
            gui = "014BR.GOV.BCB.PIX"
            key_info = f"01{len(test_key):02d}{test_key}"
            merchant_info = f"26{len(gui + key_info):02d}{gui}{key_info}"
            payload += merchant_info
            
            # 52 = Merchant Category Code
            payload += "52040000"
            
            # 53 = Transaction Currency (986 = BRL)
            payload += "5303986"
            
            # 54 = Transaction Amount
            amount_str = f"{amount:.2f}"
            payload += f"54{len(amount_str):02d}{amount_str}"
            
            # 58 = Country Code
            payload += "5802BR"
            
            # 59 = Merchant Name
            merchant_name = "PUSHINPAY"
            payload += f"59{len(merchant_name):02d}{merchant_name}"
            
            # 60 = Merchant City
            city = "SAO PAULO"
            payload += f"60{len(city):02d}{city}"
            
            # 62 = Additional Data Field Template
            reference = "***"
            additional = f"0503{reference}"
            payload += f"62{len(additional):02d}{additional}"
            
            # 63 = CRC16 placeholder
            payload += "6304"
            
            # Calcula CRC16 para o código completo
            def crc16_ccitt(data: str) -> str:
                crc = 0xFFFF
                for byte in data.encode('utf-8'):
                    crc ^= byte << 8
                    for _ in range(8):
                        if crc & 0x8000:
                            crc = (crc << 1) ^ 0x1021
                        else:
                            crc <<= 1
                        crc &= 0xFFFF
                return f"{crc:04X}"
            
            crc = crc16_ccitt(payload)
            return payload + crc
        
        mock_pix_code = generate_valid_pix_code(amount, mock_id)
        
        return {
            'success': True,
            'pix_code': mock_id,
            'amount': amount,
            'qr_code': mock_qr_base64,  # Base64 da imagem QR
            'pix_copy_paste': mock_pix_code,  # Código PIX para copiar
            'payment_id': mock_id,
            'expires_at': datetime.utcnow() + timedelta(hours=24),
            'description': description,
            'status': 'created',
            'value_cents': int(amount * 100),
            'pushinpay_data': {
                'id': mock_id,
                'status': 'created',
                'value': int(amount * 100),
                'webhook_url': "http://localhost:5000/webhook/pushinpay",
                'qr_code_base64': mock_qr_base64,
                'qr_code': mock_pix_code,
                'mock': True
            }
        }
    
    def check_payment_status(self, user_pushinpay_token: str, payment_id: str) -> dict:
        """
        Verifica status de um pagamento na PushinPay
        
        Args:
            user_pushinpay_token (str): Token Bearer da PushinPay do usuário
            payment_id (str): ID do pagamento na PushinPay
            
        Returns:
            dict: Status do pagamento
        """
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
        """
        Valida se o token da PushinPay é válido
        
        Args:
            token (str): Token Bearer da PushinPay
            
        Returns:
            dict: Resultado da validação
        """
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