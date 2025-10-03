from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from ...models.client import User
from ...database.models import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registro de novos usuários"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Validações básicas
        if not username or not email or not password:
            if request.is_json:
                return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
            flash('Todos os campos são obrigatórios', 'error')
            return render_template('auth/register.html')
        
        # Verifica se usuário já existe
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'error': 'Nome de usuário já existe'}), 400
            flash('Nome de usuário já existe', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'error': 'Email já cadastrado'}), 400
            flash('Email já cadastrado', 'error')
            return render_template('auth/register.html')
        
        # Cria novo usuário
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'message': 'Usuário criado com sucesso',
                    'user_id': user.id
                }), 201
            
            flash('Conta criada com sucesso! Faça login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'error': 'Erro ao criar usuário'}), 500
            flash('Erro ao criar usuário', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login de usuários"""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            if request.is_json:
                return jsonify({'error': 'Email e senha são obrigatórios'}), 400
            flash('Email e senha são obrigatórios', 'error')
            return render_template('auth/login.html')
        
        # Busca usuário
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            if request.is_json:
                return jsonify({
                    'message': 'Login realizado com sucesso',
                    'user_id': user.id,
                    'username': user.username
                }), 200
            
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            if request.is_json:
                return jsonify({'error': 'Credenciais inválidas'}), 401
            flash('Credenciais inválidas', 'error')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    logout_user()
    flash('Logout realizado com sucesso', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """Perfil do usuário"""
    user_data = {
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'created_at': current_user.created_at.isoformat(),
        'active_bots': current_user.get_active_bots_count(),
        'total_bots': len(current_user.bots)
    }
    
    if request.is_json:
        return jsonify(user_data)
    
    return render_template('auth/profile.html', user=user_data)

@auth_bp.route('/pushinpay-token', methods=['POST'])
@login_required
def save_pushinpay_token():
    """Salva o token da PushinPay do usuário"""
    data = request.get_json() if request.is_json else request.form
    token = data.get('token', '').strip()
    
    if not token:
        if request.is_json:
            return jsonify({'error': 'Token é obrigatório'}), 400
        flash('Token PushinPay é obrigatório', 'error')
        return redirect(url_for('auth.profile'))
    
    # Validação básica do formato do token
    if not token.startswith('Bearer '):
        if request.is_json:
            return jsonify({'error': 'Token deve começar com "Bearer "'}), 400
        flash('Token deve começar com "Bearer "', 'error')
        return redirect(url_for('auth.profile'))
    
    # Salva o token sem validação na API (para evitar dependências)
    try:
        current_user.pushinpay_token = token
        db.session.commit()
        
        if request.is_json:
            return jsonify({'message': 'Token PushinPay salvo com sucesso'})
        
        flash('Token PushinPay configurado com sucesso!', 'success')
        return redirect(url_for('auth.profile'))
        
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'error': 'Erro ao salvar token'}), 500
        flash('Erro ao salvar token', 'error')
        return redirect(url_for('auth.profile'))