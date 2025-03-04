# import pymongo
# from django.contrib.auth.backends import BaseBackend
# from django.contrib.auth.models import User
# from django.conf import settings
# import bcrypt

# class MongoDBBackend(BaseBackend):
#     def authenticate(self, request, username=None, password=None):
#         user = settings.USERS_COLLECTION.find_one({"username": username})
#         if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
#             django_user = User(username=user["username"])
#             django_user.is_authenticated = True
#             return django_user
#         return None

#     def get_user(self, user_id):
#         return None  # Since we don’t store Django users in a relational DB
from django.contrib.auth.backends import BaseBackend
from .models import CustomUser

class MongoDBBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        user = CustomUser.find_by_username(username)
        if user and user['password'] == password:  # Replace with password hashing check
            return user  # Return the MongoDB user object
        return None

    def get_user(self, user_id):
        return CustomUser.find_by_username(user_id)
