from django.conf import settings

try:
    # Ping MongoDB to test connection
    settings.MONGO_CLIENT.admin.command('ping')
    print("✅ Connected to MongoDB Atlas successfully!")
except Exception as e:
    print(f"❌ MongoDB Connection Failed: {e}")
