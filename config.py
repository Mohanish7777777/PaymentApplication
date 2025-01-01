import os
from datetime import timedelta

class Config:
    # Basic configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # MongoDB configuration
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb+srv://Rrr:Rrr23@cluster0.tyzkjzz.mongodb.net/?retryWrites=true&w=majority'
    DATABASE_NAME = 'payment_manager'

    # Security settings
    SESSION_PROTECTION = 'strong'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'payment_manager_session'
    SESSION_REFRESH_EACH_REQUEST = False
    SESSION_TYPE = 'filesystem'  # Use filesystem-based sessions
    SESSION_FILE_DIR = './flask_session'  # Directory to store session files
    SESSION_FILE_THRESHOLD = 100  # Maximum number of sessions to store
    SESSION_PERMANENT = True  # Make sessions permanent
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True

    # Application settings
    BOOTSTRAP_SERVE_LOCAL = True
