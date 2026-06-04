# from pymongo import MongoClient
# from bson.objectid import ObjectId  # Import ObjectId to handle MongoDB ObjectId

# # MongoDB connection details
# MONGO_URI = "mongodb+srv://smarthireu1:Devilai075907@smarthirecluster.ldebi.mongodb.net/?retryWrites=true&w=majority&appName=SmartHireCluster"

# # Connect to MongoDB
# client = MongoClient(MONGO_URI)

# # Access the database and collection
# MONGO_DB = client['smarthireDB']  # Use the correct database name
# jobs_collection = MONGO_DB["jobs"]

# # # Query to retrieve the _id field
# # jobs = jobs_collection.find({}, {"_id": 1})  # Only include the _id field in the result

# # # Print the _id values
# # for job in jobs:
# #     print(job["_id"])


# # Query to find the specific document by _id
# job_id = "68191ca9323dd9b394e03ea2"
# job = jobs_collection.find_one({"_id": ObjectId(job_id)})  # Use ObjectId for _id

# # Print the document
# if job:
#     print(job)
#     # print(job["job_details"])
# else:
#     print(f"No job found with _id: {job_id}")