from django.db import models

# Create your models here.
class PDFUpload(models.Model):
    pdf_file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pdf_file.name



# from pymongo import MongoClient
# from django.conf import settings
# from bson import ObjectId
# client = MongoClient(settings.MONGO_URI)
# db = client['smarthireDB']

# class MongoManager:
#     def __init__(self, collection_name):
#         self.collection = db[collection_name]

#     def save(self, data):
#         return self.collection.insert_one(data).inserted_id

#     def find_one(self, query):
#         result = self.collection.find_one(query)
#         if result and '_id' in result:
#             result['_id'] = str(result['_id'])
#         return result

#     def find_all(self, query=None):
#         results = list(self.collection.find(query or {}))
#         for result in results:
#             if '_id' in result:
#                 result['_id'] = str(result['_id'])
#         return results

#     def update(self, query, data):
#         return self.collection.update_one(query, {'$set': data})

#     def delete(self, query):
#         return self.collection.delete_one(query)

# class UserProfileManager(MongoManager):
#     def __init__(self):
#         super().__init__('user_profiles')

# class ExperienceManager(MongoManager):
#     def __init__(self):
#         super().__init__('experiences')

# class EducationManager(MongoManager):
#     def __init__(self):
#         super().__init__('educations')

# class CertificationManager(MongoManager):
#     def __init__(self):
#         super().__init__('certifications')

# class ProjectManager(MongoManager):
#     def __init__(self):
#         super().__init__('projects')

# class SkillManager(MongoManager):
#     def __init__(self):
#         super().__init__('skills')



# # from pymongo import MongoClient
# # from django.conf import settings

# # client = MongoClient(settings.MONGO_URI)
# # db = client[settings.MONGO_DB_NAME]

# # class MongoManager:
# #     def __init__(self, collection_name):
# #         self.collection = db[collection_name]

# #     def save(self, data):
# #         return self.collection.insert_one(data).inserted_id

# #     def find_one(self, query):
# #         return self.collection.find_one(query)

# #     def find_all(self, query=None):
# #         return list(self.collection.find(query or {}))

# #     def update(self, query, data):
# #         return self.collection.update_one(query, {'$set': data})

# #     def delete(self, query):
# #         return self.collection.delete_one(query)

# # class UserProfileManager(MongoManager):
# #     def __init__(self):
# #         super().__init__('user_profiles')

# # class ExperienceManager(MongoManager):
# #     def __init__(self):
# #         super().__init__('experiences')

# # class EducationManager(MongoManager):
# #     def __init__(self):
# #         super().__init__('educations')

# # class CertificationManager(MongoManager):
# #     def __init__(self):
# #         super().__init__('certifications')

# # class ProjectManager(MongoManager):
# #     def __init__(self):
# #         super().__init__('projects')

# # class SkillManager(MongoManager):
# #     def __init__(self):
# #         super().__init__('skills')