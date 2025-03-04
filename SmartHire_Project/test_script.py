from django.conf import settings
import bcrypt

# MongoDB collection
users_collection = settings.USERS_COLLECTION

# Sample user data
user_data = {
    "username": "testuser",
    "full_name": "Test User",
    "email": "test@example.com",
    "password": bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()),  # Hash password
    "role": "candidate"
}

# Insert user
users_collection.insert_one(user_data)

# print("User inserted successfully!")


# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi

# uri = "mongodb+srv://smarthireuser:Devilai075907@smarthirecluster.ldebi.mongodb.net/?retryWrites=true&w=majority&appName=SmartHireCluster"

# # Create a new client and connect to the server
# client = MongoClient(uri, server_api=ServerApi('1'))

# # Send a ping to confirm a successful connection
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)