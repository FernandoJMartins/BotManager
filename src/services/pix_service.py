import uuid
import requests
import base64
from io import BytesIO
from datetime import datetime, timedelta
from decimal import Decimal

class PushinPayService:
    """Serviço para integração com PushinPay API"""
    
    def __init__(self):
        self.api_base_url = "https://api.pushinpay.com.br/api"
        self.split_account = "9E4B259F-DB6D-419E-8D78-7216BF642856"  # Sua conta para receber o split
    
    # Taxa fixa por bot
    BOT_PRICE = Decimal('0.70')
    
    def __init__(self, pix_key: str = None):
        """
        Inicializa o serviço PIX
        
        Args:
            pix_key (str): Chave PIX para recebimento (CPF, email, telefone, etc)
        """
        # Configure sua chave PIX aqui
        self.pix_key = pix_key or "seu@email.com"  # Substitua pela sua chave PIX real
    
    def generate_pix_payment(self, user_id: int, bot_id: int, description: str = None) -> dict:
        """
        Gera um pagamento PIX para ativação de bot
        
        Args:
            user_id (int): ID do usuário
            bot_id (int): ID do bot
            description (str): Descrição do pagamento
            
        Returns:
            dict: Dados do pagamento PIX gerado
        """
        # Gera código único para o PIX
        pix_code = str(uuid.uuid4())[:8].upper()
        
        # Descrição padrão
        if not description:
            description = f"Ativacao Bot Telegram - Usuario {user_id}"
        
        # Dados do PIX
        pix_data = {
            'pix_code': pix_code,
            'amount': float(self.BOT_PRICE),
            'pix_key': self.pix_key,
            'description': description,
            'user_id': user_id,
            'bot_id': bot_id,
            'expires_at': datetime.utcnow() + timedelta(hours=24),  # Expira em 24h
            'created_at': datetime.utcnow()
        }
        
        # Gera QR Code
        qr_code_base64 = self._generate_qr_code(pix_data)
        pix_data['qr_code'] = qr_code_base64
        
        # Gera string PIX copia e cola
        pix_data['pix_copy_paste'] = self._generate_pix_string(pix_data)
        
        return pix_data
    
    def _generate_qr_code(self, pix_data: dict) -> str:
        """
        Gera QR Code para o PIX
        
        Args:
            pix_data (dict): Dados do PIX
            
        Returns:
            str: QR Code em base64
        """
        # Simplificado - em produção use um gerador PIX oficial
        pix_string = self._generate_pix_string(pix_data)
        
        # Gera QR Code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(pix_string)
        qr.make(fit=True)
        
        # Converte para imagem
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Converte para base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return img_base64
    
    def _generate_pix_string(self, pix_data: dict) -> str:
        """
        Gera string PIX copia e cola (simplificada)
        
        Args:
            pix_data (dict): Dados do PIX
            
        Returns:
            str: String PIX para copia e cola
        """
        # NOTA: Esta é uma implementação simplificada
        # Em produção, use uma biblioteca oficial para gerar PIX
        pix_string = f"""
PIX: {pix_data['pix_key']}
Valor: R$ {pix_data['amount']:.2f}
Código: {pix_data['pix_code']}
Descrição: {pix_data['description']}
        """.strip()
        
        return pix_string
    
    def validate_payment(self, pix_code: str) -> dict:
        """
        Valida se um pagamento PIX foi realizado
        
        Args:
            pix_code (str): Código do PIX
            
        Returns:
            dict: Status da validação
        """
        # NOTA: Em produção, integre com API do banco ou gateway de pagamento
        # Por enquanto, implementação simulada
        
        # Aqui você integraria com:
        # - API do seu banco
        # - Gateway de pagamento (PagSeguro, MercadoPago, etc.)
        # - Sistema de webhook para confirmação automática
        
        return {
            'status': 'pending',  # pending, completed, failed
            'message': 'Aguardando confirmação do pagamento',
            'validated_at': None
        }
    
    def check_payment_webhook(self, webhook_data: dict) -> dict:
        """
        Processa webhook de confirmação de pagamento
        
        Args:
            webhook_data (dict): Dados do webhook
            
        Returns:
            dict: Resultado do processamento
        """
        # NOTA: Implementar conforme API do provedor de pagamento
        # Exemplo de estrutura para diferentes provedores:
        
        try:
            # Extrair dados relevantes do webhook
            pix_code = webhook_data.get('reference_id')  # ou campo equivalente
            status = webhook_data.get('status')
            amount = webhook_data.get('amount')
            
            if status == 'PAID' and amount == float(self.BOT_PRICE):
                return {
                    'success': True,
                    'pix_code': pix_code,
                    'amount': amount,
                    'message': 'Pagamento confirmado'
                }
            else:
                return {
                    'success': False,
                    'message': 'Pagamento não confirmado ou valor incorreto'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Erro ao processar webhook: {str(e)}'
            }