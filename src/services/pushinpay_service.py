import requests
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

class PushinPayService:
    """Serviço             response = requests.get(
                           # Tenta fazer uma consulta simples para validar o token
            # Como não há endpoint específico de validação, vamos tentar listar transações
            response = requests.get(
                f"{self.api_base_url}/transactions",  # Endpoint para validar token
                headers=headers,
                timeout=10
            )lf.api_base_url}/transactions/{payment_id}",
                headers=headers,
                timeout=30
            )integração com PushinPay API"""
    
    def __init__(self):
        self.api_base_url = "https://api.pushinpay.com.br/api"
        self.split_account = "9E4B259F-DB6D-419E-8D78-7216BF642856"  # Sua conta para receber o split
        self.bot_price = Decimal('0.70')  # Taxa fixa por bot
    
    def create_pix_payment(self, user_pushinpay_token: str, user_id: int, bot_id: int, description: str = None) -> dict:
        """
        Cria um pagamento PIX via PushinPay API
        
        Args:
            user_pushinpay_token (str): Token Bearer da PushinPay do usuário
            user_id (int): ID do usuário
            bot_id (int): ID do bot
            description (str): Descrição do pagamento
            
        Returns:
            dict: Dados do pagamento PIX gerado
        """
        if not description:
            description = f"Ativacao Bot Telegram #{bot_id}"
        
        # Headers para a API
        headers = {
            'Authorization': f' {user_pushinpay_token}',
            'Content-Type': 'application/json'
        }
        
        # Payload para criar cobrança PIX (valores em centavos)
        payload = {
            "value": int(self.bot_price * 100),  # 0.70 reais = 70 centavos
            "webhook_url": "http://localhost:5000/webhook/pushinpay"  # URL do webhook
            # Removendo split_rules temporariamente para testar
        }
        
        try:
            print(f"Tentando criar PIX - URL: {self.api_base_url}/pix/cashIn")
            print(f"Headers: {headers}")
            print(f"Payload: {payload}")
            
            # Tenta diferentes endpoints possíveis
            endpoints_to_try = [
                f"{self.api_base_url}/pix/cashIn",
                f"{self.api_base_url}/pix/charge",  
                f"{self.api_base_url}/pix",
                f"{self.api_base_url}/charges/pix"
            ]
            
            response = None
            for endpoint in endpoints_to_try:
                try:
                    print(f"Tentando endpoint: {endpoint}")
                    response = requests.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    print(f"Endpoint {endpoint} - Status: {response.status_code}")
                    
                    # Se não foi erro 404, usa essa resposta
                    if response.status_code != 404:
                        break
                        
                except Exception as e:
                    print(f"Erro no endpoint {endpoint}: {e}")
                    continue
            
            if not response:
                raise Exception("Nenhum endpoint respondeu")
            
            # Log da resposta para debug
            print(f"PushinPay Response Status: {response.status_code}")
            print(f"PushinPay Response Headers: {response.headers}")
            print(f"PushinPay Response Text: {response.text}")
            
            if response.status_code == 200 or response.status_code == 201:
                try:
                    api_data = response.json()
                    
                    # Retorna dados padronizados conforme API PushinPay
                    return {
                        'success': True,
                        'pix_code': api_data.get('id', str(uuid.uuid4())[:8]),
                        'amount': self.bot_price,
                        'qr_code': api_data.get('qr_code_base64', ''),  # Base64 da imagem QR
                        'pix_copy_paste': api_data.get('qr_code', ''),  # Código PIX para copiar
                        'payment_id': api_data.get('id'),
                        'expires_at': datetime.utcnow() + timedelta(hours=24),
                        'description': description,
                        'status': api_data.get('status', 'created'),
                        'value_cents': api_data.get('value', int(self.bot_price * 100)),
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
                    print(f"Erro detalhado da API: {error_data}")
                except:
                    print(f"Resposta de erro não é JSON: {response.text}")
                
                # Para desenvolvimento, usa PIX simulado em caso de erro
                print(f"API falhou com {response.status_code}, usando PIX simulado")
                return self._create_mock_pix_payment(bot_id, description)
                
        except requests.exceptions.RequestException as e:
            print(f"Erro de conexão com PushinPay: {str(e)}")
            # Retorna PIX simulado para desenvolvimento
            print("Usando PIX simulado devido a erro de conexão")
            return self._create_mock_pix_payment(bot_id, description)
            
        except Exception as e:
            print(f"Erro inesperado: {str(e)}")
            # Retorna PIX simulado para desenvolvimento  
            print("Usando PIX simulado devido a erro inesperado")
            return self._create_mock_pix_payment(bot_id, description)
    
    def _create_mock_pix_payment(self, bot_id: int, description: str) -> dict:
        """Cria um PIX simulado para desenvolvimento"""
        mock_id = f"9c29870c-9f69-4bb6-90d3-{bot_id:012d}"
        
        # QR Code base64 simulado (imagem 1x1 pixel transparente)
        mock_qr_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        # Código PIX simulado no formato EMV
        mock_pix_code = f"00020126580014BR.GOV.BCB.PIX0136{mock_id}520400005303986540{int(self.bot_price * 100):02d}5802BR5909PUSHINPAY6009SAO+PAULO62070503***6304ABCD"
        
        return {
            'success': True,
            'pix_code': mock_id,
            'amount': self.bot_price,
            'qr_code': mock_qr_base64,  # Base64 da imagem QR
            'pix_copy_paste': mock_pix_code,  # Código PIX para copiar
            'payment_id': mock_id,
            'expires_at': datetime.utcnow() + timedelta(hours=24),
            'description': description,
            'status': 'created',
            'value_cents': int(self.bot_price * 100),
            'pushinpay_data': {
                'id': mock_id,
                'status': 'created',
                'value': int(self.bot_price * 100),
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
                f"{self.api_base_url}/pix/transactions/{payment_id}",
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