from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('user.user_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = db.users.find_one({'username': username})
        if user_data:
            user = User(user_data)
            if check_password_hash(user.password, password):
                login_user(user)
                if user.role == 'admin':
                    return redirect(url_for('admin.admin_dashboard'))
                return redirect(url_for('user.user_dashboard'))
        
        flash('Invalid username or password', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
            
        existing_user = db.users.find_one({'username': username})
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
            
        hashed_password = generate_password_hash(password)
        user_data = {
            'username': username,
            'password': hashed_password,
            'role': 'user'
        }
        db.users.insert_one(user_data)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
