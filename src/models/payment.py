from datetime import datetime
from ..database.models import db

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    pix_code = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.70)  # Taxa fixa de R$ 0,70
    status = db.Column(db.String(50), default='pending')  # pending, completed, failed, expired
    
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
    
    def process_payment(self):
        """Processa o pagamento e ativa o bot"""
        self.status = "completed"
        self.paid_at = datetime.utcnow()
        
        # Ativa o bot correspondente
        if self.bot:
            self.bot.is_paid = True
            self.bot.is_active = True
        
        print(f"Payment {self.pix_code} processed successfully.")
    
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