from datetime import datetime
from ..database.models import db

class CodigoVenda(db.Model):
    __tablename__ = 'codigo_venda'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Parâmetros UTM capturados da URL
    utm_campaign = db.Column(db.String(255), nullable=True)  # Campanha
    utm_source = db.Column(db.String(255), nullable=True)    # Fonte (fb, google, etc.)
    utm_medium = db.Column(db.String(255), nullable=True)    # Meio (cpc, social, etc.)  
    utm_term = db.Column(db.String(255), nullable=True)      # Termo/palavra-chave
    utm_content = db.Column(db.String(255), nullable=True)   # Conteúdo específico
    
    # Informações adicionais
    ip_address = db.Column(db.String(45), nullable=True)     # IP do usuário
    user_agent = db.Column(db.Text, nullable=True)           # User agent do navegador
    referrer = db.Column(db.String(500), nullable=True)      # Página de origem
    
    # Dados do usuário Telegram
    telegram_user_id = db.Column(db.BigInteger, nullable=False)  # ID do usuário no Telegram
    telegram_username = db.Column(db.String(100), nullable=True) # Username do Telegram
    telegram_first_name = db.Column(db.String(100), nullable=True)
    telegram_last_name = db.Column(db.String(100), nullable=True)
    
    # Status do código de venda
    status = db.Column(db.String(50), default='active')  # active, used, expired
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)      # Quando foi usado para gerar PIX
    expired_at = db.Column(db.DateTime, nullable=True)   # Quando expira (opcional)
    
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
        self.status = 'used'
        self.used_at = datetime.utcnow()
        self.payment_id = payment_id
        db.session.commit()
    
    def get_utm_data(self):
        """Retorna os dados UTM como dicionário"""
        return {
            'utm_campaign': self.utm_campaign,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_term': self.utm_term,
            'utm_content': self.utm_content,
            'ip': self.ip_address
        }
    
    def to_dict(self):
        """Converte o objeto para dicionário"""
        return {
            'id': self.id,
            'utm_campaign': self.utm_campaign,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_term': self.utm_term,
            'utm_content': self.utm_content,
            'ip_address': self.ip_address,
            'telegram_user_id': self.telegram_user_id,
            'telegram_username': self.telegram_username,
            'telegram_first_name': self.telegram_first_name,
            'telegram_last_name': self.telegram_last_name,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'bot_id': self.bot_id,
            'payment_id': self.payment_id
        }
    
    @staticmethod
    def parse_start_params(start_param):
        """
        Parseia os parâmetros do comando /start
        Suporta múltiplos separadores: |, _, -, &, ;
        Exemplos: 
        - utm_campaign=teste|utm_source=fb|utm_term=123
        - utm_campaign=teste_utm_source=fb_utm_term=123
        - utm_campaign=teste-utm_source=fb-utm_term=123
        - utm_campaign=teste&utm_source=fb&utm_term=123
        - utm_campaign=teste;utm_source=fb;utm_term=123
        """
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
        """
        Cria um novo código de venda a partir dos parâmetros do /start
        """
        utm_data = cls.parse_start_params(start_param)
        
        codigo_venda = cls(
            bot_id=bot_id,
            telegram_user_id=telegram_user.id,
            telegram_username=telegram_user.username,
            telegram_first_name=telegram_user.first_name,
            telegram_last_name=telegram_user.last_name,
            utm_campaign=utm_data.get('utm_campaign'),
            utm_source=utm_data.get('utm_source'),
            utm_medium=utm_data.get('utm_medium'),
            utm_term=utm_data.get('utm_term'),
            utm_content=utm_data.get('utm_content'),
            ip_address=utm_data.get('ip')
        )
        
        db.session.add(codigo_venda)
        db.session.commit()
        
        return codigo_venda