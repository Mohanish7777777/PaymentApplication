from flask_login import LoginManager
from bson.objectid import ObjectId
from models import User
from database import db

# Initialize LoginManager
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None
