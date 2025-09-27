from datetime import datetime
from ..database.models import db

class TelegramBot(db.Model):
    __tablename__ = 'telegram_bots'
    
    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(255), unique=True, nullable=False)
    bot_username = db.Column(db.String(100), nullable=True)
    bot_name = db.Column(db.String(100), nullable=True)
    
    # Configurações do bot
    welcome_message = db.Column(db.Text, nullable=True, default="Olá! Bem-vindo ao meu bot!")
    welcome_image = db.Column(db.String(500), nullable=True)  # File ID do Telegram
    welcome_audio = db.Column(db.String(500), nullable=True)  # File ID do Telegram
    pix_values = db.Column(db.JSON, nullable=True, default='[]')  # Lista de valores para PIX [10.0, 20.0, 50.0]
    plan_names = db.Column(db.JSON, nullable=True, default='[]')  # Lista de nomes dos planos ["VIP SEMANAL", "PREMIUM MENSAL"]
    
    # Status e controle
    is_active = db.Column(db.Boolean, default=True)  # Bot está ativo quando criado
    is_running = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, nullable=True)
    
    # Foreign Key para usuário
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relacionamento com pagamentos
    payments = db.relationship('Payment', backref='bot', lazy=True)
    
    def start_bot(self):
        """Inicia o bot Telegram"""
        if not self.is_running and self.is_active:
            self.is_running = True
            self.last_activity = datetime.utcnow()
            print(f"Bot {self.bot_username} iniciado.")
            return True
        return False
    
    def stop_bot(self):
        """Para o bot Telegram"""
        if self.is_running:
            self.is_running = False
            print(f"Bot {self.bot_username} parado.")
            return True
        return False
    
    def get_status(self) -> str:
        if not self.is_active:
            return "Inativo"
        return "Rodando" if self.is_running else "Parado"
    
    def get_pix_values(self) -> list:
        """Retorna lista de valores PIX configurados"""
        try:
            if isinstance(self.pix_values, str):
                import json
                return json.loads(self.pix_values)
            return self.pix_values or []
        except:
            return []
    
    def get_plan_names(self) -> list:
        """Retorna lista de nomes dos planos configurados"""
        try:
            if isinstance(self.plan_names, str):
                import json
                return json.loads(self.plan_names)
            return self.plan_names or []
        except:
            return []
    
    def __repr__(self):
        return f"TelegramBot(username={self.bot_username}, active={self.is_active})"