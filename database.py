from pymongo import MongoClient
from config import Config

# Initialize MongoDB
mongo_client = MongoClient(Config.MONGO_URI)
db = mongo_client[Config.DATABASE_NAME]
