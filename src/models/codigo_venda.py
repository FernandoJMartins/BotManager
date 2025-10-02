from datetime import datetime
from ..database.models import db

class CodigoVenda(db.Model):
    __tablename__ = 'codigo_venda'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dados do usuário Telegram
    telegram_user_id = db.Column(db.BigInteger, nullable=False)  # ID do usuário no Telegram
    telegram_username = db.Column(db.String(100), nullable=True) # Username do Telegram
    telegram_first_name = db.Column(db.String(100), nullable=True)
    telegram_last_name = db.Column(db.String(100), nullable=True)
    
    unique_click_id = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Foreign Keys
    bot_id = db.Column(db.Integer, db.ForeignKey('telegram_bots.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)  # Relaciona com pagamento quando PIX é gerado
    
    # Relacionamentos
    bot = db.relationship('TelegramBot', backref='codigos_venda')
    payment = db.relationship('Payment', backref='codigo_venda', uselist=False)
    
    def __init__(self, **kwargs):
        super(CodigoVenda, self).__init__(**kwargs)
    
    def mark_as_used(self, payment_id):
        """Marca o código de venda como usado e associa ao pagamento"""

        self.payment_id = payment_id
        db.session.commit()
    
    # def get_utm_data(self):
        # return {
        #     'utm_campaign': self.utm_campaign,
        #     'utm_source': self.utm_source,
        #     'utm_medium': self.utm_medium,
        #     'utm_term': self.utm_term,
        #     'utm_content': self.utm_content,
        #     'ip': self.ip_address
        # }
   
    
    @staticmethod
    def parse_start_params(start_param):
        utm_data = {}
        
        if not start_param:
            return utm_data
            
        try:
            params = []

            # Se não encontrou nenhum separador, trata como um parâmetro único
            if not params:
                params = [start_param]
            
            for param in params:
                if '=' in param:
                    key, value = param.split('=', 1)  # Split apenas na primeira ocorrência de =
                    utm_data[key.strip()] = value.strip()
                    
        except Exception as e:
            print(f"Erro ao parsear parâmetros UTM: {e}")
            
        return utm_data
    
    @classmethod
    def create_from_start_params(cls, bot_id, telegram_user, start_param):

        codigo_venda = cls(
            bot_id=bot_id,
            telegram_user_id=telegram_user.id,
            telegram_username=telegram_user.username,
            telegram_first_name=telegram_user.first_name,
            telegram_last_name=telegram_user.last_name,
            unique_click_id=start_param
        )
        
        db.session.add(codigo_venda)
        db.session.commit()
        
        return codigo_venda