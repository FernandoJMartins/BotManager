from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from ..database.models import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    pushinpay_token = db.Column(db.String(255), nullable=True)  # Token Bearer da PushinPay
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship com bots
    bots = db.relationship('TelegramBot', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_active_bots_count(self):
        return len([bot for bot in self.bots if bot.is_active])
    
    def can_add_bot(self):
        return self.get_active_bots_count() < 30
    
    def __repr__(self):
        return f"User(username={self.username}, email={self.email})"