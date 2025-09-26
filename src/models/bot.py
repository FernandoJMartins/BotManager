from datetime import datetime
from ..database.models import db

class TelegramBot(db.Model):
    __tablename__ = 'telegram_bots'
    
    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(255), unique=True, nullable=False)
    bot_username = db.Column(db.String(100), nullable=True)
    bot_name = db.Column(db.String(100), nullable=True)
    
    # Configurações do bot
    welcome_message = db.Column(db.Text, nullable=True)
    welcome_image = db.Column(db.String(255), nullable=True)  # Path para arquivo
    welcome_audio = db.Column(db.String(255), nullable=True)  # Path para arquivo
    pix_values = db.Column(db.JSON, nullable=True)  # Lista de valores para PIX
    
    # Status e controle
    is_active = db.Column(db.Boolean, default=False)
    is_running = db.Column(db.Boolean, default=False)
    is_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, nullable=True)
    
    # Foreign Key para usuário
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relacionamento com pagamentos
    payments = db.relationship('Payment', backref='bot', lazy=True)
    
    def start(self):
        if not self.is_running and self.is_paid:
            self.is_running = True
            self.last_activity = datetime.utcnow()
            print(f"Bot {self.bot_username} started.")
    
    def stop(self):
        if self.is_running:
            self.is_running = False
            print(f"Bot {self.bot_username} stopped.")
    
    def get_status(self) -> str:
        if not self.is_paid:
            return "Pagamento Pendente"
        return "Ativo" if self.is_running else "Inativo"
    
    def __repr__(self):
        return f"TelegramBot(username={self.bot_username}, active={self.is_active})"