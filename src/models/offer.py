from datetime import datetime
from ..database.models import db

class Offer(db.Model):
    __tablename__ = 'offers'
    
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('telegram_bots.id', ondelete='CASCADE'), nullable=False)
    offer_type = db.Column(db.String(20), nullable=False)  # 'order_bump', 'downsell', 'mailing'
    name = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    deliverable_message = db.Column(db.Text, nullable=True)
    
    # Mídias (File IDs do Telegram)
    media_image_file_id = db.Column(db.String(255), nullable=True)
    media_video_file_id = db.Column(db.String(255), nullable=True)
    media_audio_file_id = db.Column(db.String(255), nullable=True)
    
    # Textos dos botões
    accept_button_text = db.Column(db.String(100), default='✅ Aceitar Oferta')
    decline_button_text = db.Column(db.String(100), default='❌ Não, obrigado')
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos - REMOVIDO back_populates que causava conflito
    bot = db.relationship('TelegramBot', backref='offers')
    order_bump_config = db.relationship('OrderBumpConfig', uselist=False, cascade='all, delete-orphan')
    downsell_config = db.relationship('DownsellConfig', uselist=False, cascade='all, delete-orphan')
    mailing_config = db.relationship('MailingConfig', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Offer {self.name} ({self.offer_type})>'


class OrderBumpConfig(db.Model):
    __tablename__ = 'order_bump_config'
    
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False, unique=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # REMOVIDO back_populates que causava conflito
    offer = db.relationship('Offer')


class DownsellConfig(db.Model):
    __tablename__ = 'downsell_config'
    
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False, unique=True)
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=False)
    delay_minutes = db.Column(db.JSON, nullable=False)  # [15, 30, 60]
    
    # REMOVIDO back_populates que causava conflito
    offer = db.relationship('Offer')


class MailingConfig(db.Model):
    __tablename__ = 'mailing_config'
    
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False, unique=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    target_audience = db.Column(db.String(50), nullable=False)  # 'all', 'interacted', 'unpaid'
    
    # REMOVIDO back_populates que causava conflito
    offer = db.relationship('Offer')


class OfferPayment(db.Model):
    __tablename__ = 'offer_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    offer_amount = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    offer = db.relationship('Offer', backref='payments')
    payment = db.relationship('Payment', backref='offer_payments')


class DownsellSchedule(db.Model):
    __tablename__ = 'downsell_schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    offer_id = db.Column(db.Integer, db.ForeignKey('offers.id', ondelete='CASCADE'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    calculated_values = db.Column(db.JSON, nullable=False)  # [16.00, 8.00, 24.00]
    scheduled_for = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'sent', 'cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    offer = db.relationship('Offer', backref='downsell_schedules')
    payment = db.relationship('Payment', backref='downsell_schedules')