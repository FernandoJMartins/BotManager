from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Inicialização do SQLAlchemy
db = SQLAlchemy()

# Inicialização do Login Manager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

def init_db(app):
    """Inicializa o banco de dados com a aplicação Flask"""
    db.init_app(app)
    login_manager.init_app(app)
    
    with app.app_context():
        # Importa todos os modelos para garantir que as tabelas sejam criadas
        from ..models.client import User
        from ..models.bot import TelegramBot
        from ..models.payment import Payment
        
        # Cria todas as tabelas
        db.create_all()
        
        print("Database tables created successfully!")

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário para o Flask-Login"""
    from ..models.client import User
    return User.query.get(int(user_id))