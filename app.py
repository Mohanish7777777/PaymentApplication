from flask import Flask, redirect, url_for
from flask_bootstrap import Bootstrap
from extensions import db, login_manager
from werkzeug.security import generate_password_hash
from models import User

app = Flask(__name__)
app.config.from_object('config.Config')

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

def create_admin_user():
    admin_exists = db.users.find_one({'username': 'admin'})
    if admin_exists:
        print("Admin user already exists")
    else:
        admin_data = {
            'username': 'admin',
            'password': generate_password_hash('admin123'),
            'role': 'admin'
        }
        db.users.insert_one(admin_data)
        print("Admin user created successfully")

# Initialize admin user
create_admin_user()

# Initialize extensions
login_manager.init_app(app)
bootstrap = Bootstrap(app)

# Initialize session
from flask_session import Session
Session(app)

# Import routes
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.payment import payment_bp
from routes.ticket import ticket_bp
from routes.user import user_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(ticket_bp)
app.register_blueprint(user_bp)

if __name__ == '__main__':
    app.run(debug=True)
