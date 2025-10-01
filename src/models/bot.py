from datetime import datetime
from ..database.models import db

class TelegramBot(db.Model):
    __tablename__ = 'telegram_bots'
    
    id = db.Column(db.Integer, primary_key=True)
    bot_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    bot_username = db.Column(db.String(100), nullable=True)  # Pode ser None
    bot_name = db.Column(db.String(100), nullable=True)
    
    # Configurações do bot
    welcome_message = db.Column(db.Text, nullable=True, default="Olá! Bem-vindo ao meu bot!")
    
    # Mídia armazenada no Telegram (file_id)
    welcome_image_file_id = db.Column(db.String(255), nullable=True)  # File ID do Telegram para imagem
    welcome_audio_file_id = db.Column(db.String(255), nullable=True)  # File ID do Telegram para áudio
    welcome_video_file_id = db.Column(db.String(255), nullable=True)  # File ID do Telegram para vídeo
    
    # Identificador único para evitar cruzamento de dados entre bots
    media_identifier = db.Column(db.String(100), nullable=True)
    
    # Campos antigos (mantidos para compatibilidade/backup)
    welcome_image = db.Column(db.String(500), nullable=True)  # DEPRECATED: usar welcome_image_file_id
    welcome_audio = db.Column(db.String(500), nullable=True)  # DEPRECATED: usar welcome_audio_file_id
    
    pix_values = db.Column(db.JSON, nullable=True, default='[]')  # Lista de valores para PIX [10.0, 20.0, 50.0]
    plan_names = db.Column(db.JSON, nullable=True, default='[]')  # Lista de nomes dos planos ["VIP SEMANAL", "PREMIUM MENSAL"]
    plan_duration = db.Column(db.JSON, nullable =True, default='[]')

    id_vip = db.Column(db.String(255))
    id_logs = db.Column(db.String(255))

    # Status e controle
    is_active = db.Column(db.Boolean, default=True)  # Bot está ativo quando criado
    is_running = db.Column(db.Boolean, default=True)
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
    
    def get_plan_durations(self) -> list:
        """Retorna lista de durações dos planos configurados"""
        try:
            if isinstance(self.plan_duration, str):
                import json
                return json.loads(self.plan_duration)
            return self.plan_duration or []
        except:
            return []
    
    def has_vip_group(self) -> bool:
        """Verifica se o bot tem grupo VIP configurado"""
        return bool(self.id_vip and self.id_vip.strip())
    
    def has_log_group(self) -> bool:
        """Verifica se o bot tem grupo de logs configurado"""
        return bool(self.id_logs and self.id_logs.strip())
    
    def get_vip_group_id(self) -> str:
        """Retorna ID do grupo VIP formatado"""
        if self.has_vip_group():
            # Garante que o ID está no formato correto
            group_id = self.id_vip.strip()
            if not group_id.startswith('-'):
                group_id = f"-{group_id}"
            return group_id
        return None
    
    def get_log_group_id(self) -> str:
        """Retorna ID do grupo de logs formatado"""
        if self.has_log_group():
            # Garante que o ID está no formato correto
            group_id = self.id_logs.strip()
            if not group_id.startswith('-'):
                group_id = f"-{group_id}"
            return group_id
        return None
    
    def has_welcome_image(self) -> bool:
        """Verifica se o bot tem imagem de boas-vindas configurada"""
        return bool(self.welcome_image_file_id or self.welcome_image)
    
    def has_welcome_audio(self) -> bool:
        """Verifica se o bot tem áudio de boas-vindas configurado"""
        return bool(self.welcome_audio_file_id or self.welcome_audio)
    
    def get_welcome_image_id(self) -> str:
        """Retorna o file_id da imagem de boas-vindas (novo sistema) ou caminho (compatibilidade)"""
        return self.welcome_image_file_id or self.welcome_image
    
    def get_welcome_audio_id(self) -> str:
        """Retorna o file_id do áudio de boas-vindas (novo sistema) ou caminho (compatibilidade)"""
        return self.welcome_audio_file_id or self.welcome_audio
    
    def set_welcome_media(self, media_type: str, file_id: str, mime_type: str = None, file_size: int = None):
        """Define mídia de boas-vindas usando file_id do Telegram"""
        if media_type == 'image':
            self.welcome_image_file_id = file_id
            self.welcome_image_type = mime_type
            self.welcome_image_size = file_size
        elif media_type == 'audio':
            self.welcome_audio_file_id = file_id
            self.welcome_audio_type = mime_type
            self.welcome_audio_size = file_size
    
    def is_fully_configured(self) -> bool:
        """Verifica se o bot está completamente configurado"""
        return (
            bool(self.bot_token) and
            bool(self.bot_username) and
            self.has_vip_group() and
            self.has_log_group() and
            bool(self.get_pix_values())
        )
    
    def has_welcome_media(self) -> bool:
        """Verifica se o bot tem mídia de boas-vindas configurada"""
        return bool(self.welcome_image_file_id or self.welcome_audio_file_id or self.welcome_video_file_id)
    
    def get_media_identifier(self) -> str:
        """Retorna ou gera identificador único para mídia do bot"""
        if not self.media_identifier:
            import uuid
            self.media_identifier = f"bot_{self.id}_{str(uuid.uuid4())[:8]}"
        return self.media_identifier
    
    def get_welcome_media_info(self) -> dict:
        """Retorna informações sobre a mídia de boas-vindas"""
        return {
            'has_image': bool(self.welcome_image_file_id),
            'has_audio': bool(self.welcome_audio_file_id),
            'has_video': bool(self.welcome_video_file_id),
            'image_file_id': self.welcome_image_file_id,
            'audio_file_id': self.welcome_audio_file_id,
            'video_file_id': self.welcome_video_file_id,
            'identifier': self.get_media_identifier()
        }
    
    def get_username_formatted(self) -> str:
        """Retorna o username formatado com @ se não tiver"""
        if not self.bot_username:
            return "Bot sem username"
        
        username = self.bot_username.strip()
        if username and not username.startswith('@'):
            return f"@{username}"
        return username
    
    def get_username_clean(self) -> str:
        """Retorna o username sem @ para uso em APIs"""
        if not self.bot_username:
            return ""
        
        return self.bot_username.replace('@', '').strip()
    
    def set_username_from_telegram(self, telegram_username: str):
        """Define o username a partir dos dados do Telegram"""
        if telegram_username:
            username = telegram_username.strip()
            if not username.startswith('@'):
                username = f"@{username}"
            self.bot_username = username
    
    def __init__(self, **kwargs):
        """Inicialização customizada para validar dados"""
        # Import do logger dentro do método para evitar imports circulares
        try:
            from ..utils.logger import logger
            logger.info(f"🏗️ Criando TelegramBot com dados: {kwargs}")
        except ImportError:
            print(f"🏗️ Criando TelegramBot com dados: {kwargs}")
        
        # Chama o init da classe pai
        super().__init__(**kwargs)
        
        # Log dos dados após inicialização
        try:
            from ..utils.logger import logger
            logger.info(f"🏗️ TelegramBot criado:")
            logger.info(f"   - Token: {self.bot_token[:10] if self.bot_token else 'None'}...")
            logger.info(f"   - Username: {self.bot_username}")
            logger.info(f"   - Name: {self.bot_name}")
            logger.info(f"   - User ID: {self.user_id}")
        except ImportError:
            print(f"🏗️ TelegramBot criado:")
            print(f"   - Token: {self.bot_token[:10] if self.bot_token else 'None'}...")
            print(f"   - Username: {self.bot_username}")
            print(f"   - Name: {self.bot_name}")
            print(f"   - User ID: {self.user_id}")
    
    def __repr__(self):
        return f"TelegramBot(username={self.get_username_formatted()}, active={self.is_active})"