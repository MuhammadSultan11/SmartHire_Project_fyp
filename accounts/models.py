# from django.db import models

# # Create your models here.
# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class CustomUser(AbstractUser):
#     ROLE_CHOICES = (
#         ('hr', 'HR'),
#         ('candidate', 'Candidate'),
#     )
#     role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    
#     def __str__(self):
#         return self.username


import pymongo
from django.conf import settings

# MongoDB Collection
USERS_COLLECTION = settings.USERS_COLLECTION

class CustomUser:
    def __init__(self, username, email, role, password=None):
        self.username = username
        self.email = email
        self.role = role
        self.password = password  # Should be hashed before saving

    def save(self):
        """ Save user to MongoDB """
        user_data = {
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "password": self.password  # Store hashed password
        }
        USERS_COLLECTION.insert_one(user_data)

    @staticmethod
    def find_by_username(username):
        """ Find user by username """
        return USERS_COLLECTION.find_one({"username": username})

    @staticmethod
    def find_by_email(email):
        """ Find user by email """
        return USERS_COLLECTION.find_one({"email": email})

    def __str__(self):
        return self.username
