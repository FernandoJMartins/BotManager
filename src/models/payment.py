from datetime import datetime
from ..database.models import db

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    pix_code = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Valor escolhido pelo cliente final
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed, expired
    payment_platform = db.Column(db.String(50), default='pushinpay')  # pushinpay, mercadopago, stripe, etc.
    
    # Informações do cliente final serão capturadas via webhook
    
    # Dados do PIX
    pix_key = db.Column(db.String(255), nullable=True)
    pix_qr_code = db.Column(db.Text, nullable=True)  # Base64 da imagem QR
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bot_id = db.Column(db.Integer, db.ForeignKey('telegram_bots.id'), nullable=False)
    
    def get_platform_fees(self):
        """Retorna as taxas da plataforma de pagamento"""
        platform_fee = 0.70  # Taxa fixa da sua plataforma
        
        # Taxas por plataforma de pagamento
        payment_platform_fees = {
            'pushinpay': 0.30,
            'mercadopago': 0.40,  # Exemplo para futuras plataformas
            'stripe': 0.35,       # Exemplo para futuras plataformas
            'pagseguro': 0.45,    # Exemplo para futuras plataformas
        }
        
        payment_platform_fee = payment_platform_fees.get(self.payment_platform, 0.30)
        return platform_fee + payment_platform_fee
    
    def get_net_amount(self):
        """Retorna o valor líquido após deduzir as taxas"""
        return self.amount - self.get_platform_fees()
    
    def process_payment(self):
        """Processa o pagamento do cliente final"""
        self.status = "completed"
        self.paid_at = datetime.utcnow()
        
        print(f"Pagamento {self.pix_code} de R$ {self.amount} confirmado para @{self.telegram_username}")
    
    def is_expired(self):
        """Verifica se o pagamento expirou"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def get_status(self) -> str:
        if self.is_expired() and self.status == 'pending':
            return 'expired'
        return self.status
    
    def __repr__(self):
        return f"Payment(pix_code={self.pix_code}, amount={self.amount}, status={self.status})"