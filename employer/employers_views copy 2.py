import json
from msvcrt import get_osfhandle
from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import login_required
from accounts.accounts_views import mongo_login_required  # Import from accounts_views.py
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
from django.http import JsonResponse
import pymongo
from bson import ObjectId
import re
from django.conf import settings 
import google.generativeai as genai
import logging
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse



# Constants
RESUMES_COLLECTION = 'resumes'
PROCESSED_RESUMES_COLLECTION = 'processed_resumes'
TEMP_APPLICATIONS_COLLECTION = 'temp_applications'
APPLICATIONS_COLLECTION = 'applications'
JOBS_COLLECTION = 'jobs'
RESUMES_EVALUATION_COLLECTION = 'resumes_evaluation'
USER_ACTIVITY_LOGS_COLLECTION = 'user_activity_logs'
POSITION_TITLES_COLLECTION = 'position_titles'  # New collection
JOB_STATUS_OPEN = 'Open'
JOB_STATUS_DRAFT = 'Draft'

APPLICATION_STATUS_SUBMITTED = 'submitted'
SUBMISSION_METHOD_MANUAL = 'manual_edit'
EVALUATION_STATUS_EVALUATED = 'Evaluated'
EVALUATOR_TYPE_AUTOMATED = 'Automated'
EVALUATOR_DETAILS_GEMINI = 'Gemini-1.5-flash'


logger = logging.getLogger(__name__)

try:
    from django.conf import settings
    jobs_collection = settings.MONGO_DB["jobs"]
except AttributeError as e:
    raise Exception("MONGO_DB not configured in settings. Ensure MongoDB is set up correctly.")


# def map_priorities_to_weights(priorities):
#     PRIORITY_MAPPING = {
#         "High": 0.35,
#         "Medium": 0.20,
#         "Low": 0.10,
#         "None": 0.05
#     }
#     required_keys = {"skills", "experience", "education", "projects", "soft_skills", "additional_info"}
#     if set(priorities.keys()) != required_keys:
#         return None, f"Missing or extra priority keys: {required_keys}"
        
#     high_count = sum(1 for p in priorities.values() if p == "High")
#     if high_count == 0:
#         return None, "At least one component must have High priority"
    
#     weights = {}
#     for key, priority in priorities.items():
#         if priority not in PRIORITY_MAPPING:
#             return None, f"Invalid priority for {key}: {priority}"
#         weights[key] = PRIORITY_MAPPING[priority]
        
#     total = sum(weights.values())
#     if total == 0:
#         return None, "All weights are zero"
        
#     weights = {k: v / total for k, v in weights.items()}
        
#     for key, value in weights.items():
#         if not (0.05 <= value <= 0.40):
#             return None, f"Weight for {key} ({value:.2f}) must be between 0.05 and 0.40"
    
#     return weights, ""


def map_priorities_to_weights(priorities):
    PRIORITY_MAPPING = {
        "High": 0.35,
        "Medium": 0.20,
        "Low": 0.10,
        "None": 0.05
    }
    required_keys = {"skills", "experience", "education", "projects", "soft_skills", "additional_info"}
    if set(priorities.keys()) != required_keys:
        return None, f"Missing or extra priority keys: {required_keys}"
    
    high_count = sum(1 for p in priorities.values() if p == "High")
    if high_count == 0:
        return None, "At least one component must have High priority"
    
    weights = {}
    for key, priority in priorities.items():
        if priority not in PRIORITY_MAPPING:
            return None, f"Invalid priority for {key}: {priority}"
        weights[key] = PRIORITY_MAPPING[priority]
    
    total = sum(weights.values())
    if total == 0:
        return None, "All weights are zero"
    
    weights = {k: v / total for k, v in weights.items()}
    
    for key, value in weights.items():
        if not (0.05 <= value <= 0.40):
            return None, f"Weight for {key} ({value:.2f}) must be between 0.05 and 0.40"
    
    return weights, ""



@mongo_login_required
def job_postform_view(request):
    if request.method == "POST":
        data = request.POST
        errors = {}

        # Extract and validate data
        job_details = {
            "position_title": data.get("job_details[position_title]"),
            "position_title_new": data.get("job_details[position_title_new]", ""),
            "job_description": data.get("job_details[job_description]"),
        }

        # Enhanced requirements with min_years for technical skills
        requirements = {
            "technical_skills": [
                {"name": skill, "min_years": int(data.get(f"requirements[technical_skills][{i}][min_years]", 0))}
                for i, skill in enumerate(data.getlist("requirements[technical_skills][]"))
                if skill.strip()  # Filter out empty skills
            ],
            "soft_skills": [skill for skill in data.getlist("requirements[soft_skills][]") if skill.strip()],
            "threshold": data.get("requirements[threshold]", "0"),
        }

        priorities = {
            "skills": data.get("weights[skills]", "Medium"),
            "experience": data.get("weights[experience]", "Medium"),
            "education": data.get("weights[education]", "Low"),
            "projects": data.get("weights[projects]", "Low"),
            "soft_skills": data.get("weights[soft_skills]", "None"),
            "additional_info": data.get("weights[additional_info]", "None"),
        }

        weights, weight_error = map_priorities_to_weights(priorities)
        if weight_error:
            errors["skills_priority"] = weight_error
            logger.error(f"Priority validation failed: {weight_error}")

        experience = []
        for i in range(100):
            role = data.get(f"experience[{i}][role]")
            if not role:
                break
            experience.append({
                "role": role,
                "role_new": data.get(f"experience[{i}][role_new]", ""),
                "years": int(data.get(f"experience[{i}][years]", "0")) or 0,
            })

        education = []
        for i in range(100):
            degree = data.get(f"education[{i}][degree]")
            if not degree:
                break
            education.append({
                "degree": degree,
                "degree_new": data.get(f"education[{i}][degree_new]", ""),
            })

        certifications = []
        for i in range(100):
            name = data.get(f"certifications[{i}][name]")
            if not name:
                break
            certifications.append({
                "name": name,
            })

        job_type = {
            "type": data.get("job_type[type]"),
            "work_arrangement": data.get("job_type[work_arrangement]"),
            "openings": data.get("job_type[openings]", "1"),
        }

        compensation = {
            "min_salary": data.get("compensation[min_salary]", "0"),
            "max_salary": data.get("compensation[max_salary]", "0"),
            "currency": data.get("compensation[currency]"),
            "location": data.get("compensation[location]", ""),
        }

        additional_info = {
            "contact_information": data.get("additional_info[contact_information]"),
        }

        company_details = {
            "name": data.get("company_details[name]"),
            "website": data.get("company_details[website]"),
            "overview": data.get("company_details[overview]"),
        }

        benefits = {
            "offered": data.get("benefits[offered]"),
        }

        # New: Application deadline
        application_deadline = data.get("application_deadline", "")

        # Validation
        if not job_details["position_title"] or (job_details["position_title"] == "add-new" and not job_details["position_title_new"]):
            errors["position_title"] = "Position title is required."
        if not job_details["job_description"]:
            errors["job_description"] = "Job description is required."
        if not requirements["technical_skills"]:
            errors["technical_skills"] = "At least one technical skill is required."
        if not requirements["threshold"].isdigit() or int(requirements["threshold"]) < 0 or int(requirements["threshold"]) > 100:
            errors["threshold"] = "Threshold must be between 0 and 100."
        if not job_type["type"]:
            errors["job_type"] = "Job type is required."
        if not job_type["work_arrangement"]:
            errors["work_arrangement"] = "Work arrangement is required."
        if not job_type["openings"].isdigit() or int(job_type["openings"]) < 1:
            errors["openings"] = "Number of openings must be at least 1."
        if not compensation["min_salary"].isdigit() or int(compensation["min_salary"]) < 0:
            errors["salary"] = "Minimum salary cannot be negative."
        if not compensation["max_salary"].isdigit() or int(compensation["max_salary"]) < 0:
            errors["salary"] = "Maximum salary cannot be negative."
        if int(compensation["min_salary"]) > int(compensation["max_salary"]) and int(compensation["max_salary"]) != 0:
            errors["salary"] = "Minimum salary cannot exceed maximum salary."
        if not compensation["currency"]:
            errors["currency"] = "Currency is required."
        if job_type["work_arrangement"] in ["Hybrid", "Onsite"] and not compensation["location"]:
            errors["location"] = "Location is required for Hybrid or Onsite arrangements."
        if not company_details["name"]:
            errors["company_name"] = "Company name is required."
        if company_details["website"] and not re.match(r"^https?://", company_details["website"]):
            errors["company_website"] = "Invalid URL format (e.g., https://example.com)."
        if application_deadline and not re.match(r"^\d{4}-\d{2}-\d{2}$", application_deadline):
            errors["application_deadline"] = "Invalid date format (YYYY-MM-DD)."

        if errors:
            logger.error(f"Validation errors: {errors}")
            return JsonResponse({"success": False, "errors": errors}, status=400)

        # Convert string values to appropriate types
        requirements["threshold"] = int(requirements["threshold"])
        job_type["openings"] = int(job_type["openings"])
        compensation["min_salary"] = int(compensation["min_salary"])
        compensation["max_salary"] = int(compensation["max_salary"])
        application_deadline = datetime.datetime.strptime(application_deadline, "%Y-%m-%d") if application_deadline else None

        # Prepare document for MongoDB
        job_document = {
            "job_details": {
                "position_title": job_details["position_title_new"] if job_details["position_title"] == "add-new" else job_details["position_title"],
                "job_description": job_details["job_description"],
            },
            "requirements": requirements,
            "experience": experience if experience else [],
            "education": [edu | {"degree": edu["degree_new"] if edu["degree"] == "add-new" else edu["degree"]} for edu in education] if education else [],
            "certifications": certifications if certifications else [],
            "job_type": job_type,
            "compensation": compensation,
            "additional_info": additional_info,
            "company_details": company_details,
            "benefits": benefits,
            "weights": weights,
            "posted_by": request.mongo_user['user_id'],  # Use mongo_user from mongo_login_required
            "application_count": 0,
            "status": JOB_STATUS_OPEN if additional_info.get("posting_status") == "Active" else JOB_STATUS_DRAFT,
            "application_deadline": application_deadline,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
        }

        # Save to MongoDB
        try:
            result = settings.MONGO_DB[JOBS_COLLECTION].insert_one(job_document)
            job_id = str(result.inserted_id)

            # Log user activity
            settings.MONGO_DB[USER_ACTIVITY_LOGS_COLLECTION].insert_one({
                "user_id": request.mongo_user['user_id'],
                "action": "job_posted",
                "details": {
                    "job_id": job_id,
                    "position_title": job_document["job_details"]["position_title"],
                    "timestamp": datetime.datetime.now().isoformat(),
                },
                "created_at": datetime.datetime.now().isoformat(),
            })

            logger.info(f"Job posted successfully: {job_id} by user {request.mongo_user['user_id']}")
            return JsonResponse({"success": True, "message": "Job posted successfully!", "job_id": job_id})
        except Exception as e:
            logger.error(f"Failed to save job to MongoDB: {str(e)}", exc_info=True)
            return JsonResponse({"success": False, "errors": {"general": "Failed to save job posting."}}, status=500)

    # Handle GET request
    return render(request, "employer/job_form.html")



# def job_postform_view(request):
#     if request.method == "POST":
#         data = request.POST
#         errors = {}

#         # Extract and validate data
#         job_details = {
#             "position_title": data.get("job_details[position_title]"),
#             "position_title_new": data.get("job_details[position_title_new]", ""),
#             "job_description": data.get("job_details[job_description]"),
#         }

#         requirements = {
#             "technical_skills": data.getlist("requirements[technical_skills][]"),
#             "soft_skills": data.getlist("requirements[soft_skills][]"),
#             "threshold": data.get("requirements[threshold]", "0"),  # Default to "0" as string
#         }

#         # Extract priorities
#         priorities = {
#             "skills": data.get("weights[skills]", "Medium"),  # Default to "Medium"
#             "experience": data.get("weights[experience]", "Medium"),
#             "education": data.get("weights[education]", "Low"),
#             "projects": data.get("weights[projects]", "Low"),
#             "soft_skills": data.get("weights[soft_skills]", "None"),
#             "additional_info": data.get("weights[additional_info]", "None"),
#         }

#         weights, weight_error = map_priorities_to_weights(priorities)
#         if weight_error:
#             errors["skills_priority"] = weight_error
#             logger.error(f"Priority validation failed: {weight_error}")

#         experience = []
#         for i in range(100):
#             role = data.get(f"experience[{i}][role]")
#             if not role:
#                 break
#             experience.append({
#                 "role": role,
#                 "role_new": data.get(f"experience[{i}][role_new]", ""),
#                 "years": int(data.get(f"experience[{i}][years]", "0")) or 0,
#             })

#         education = []
#         for i in range(100):
#             degree = data.get(f"education[{i}][degree]")
#             if not degree:
#                 break
#             education.append({
#                 "degree": degree,
#                 "degree_new": data.get(f"education[{i}][degree_new]", ""),
#             })

#         certifications = []
#         for i in range(100):
#             name = data.get(f"certifications[{i}][name]")
#             if not name:
#                 break
#             certifications.append({
#                 "name": name,
#             })

#         job_type = {
#             "type": data.get("job_type[type]"),
#             "work_arrangement": data.get("job_type[work_arrangement]"),
#             "openings": data.get("job_type[openings]", "1"),  # Default to "1"
#         }

#         compensation = {
#             "min_salary": data.get("compensation[min_salary]", "0"),  # Default to "0"
#             "max_salary": data.get("compensation[max_salary]", "0"),  # Default to "0"
#             "currency": data.get("compensation[currency]"),
#             "location": data.get("compensation[location]", ""),
#         }

#         additional_info = {
#             "contact_information": data.get("additional_info[contact_information]"),
#             "posting_status": data.get("additional_info[posting_status]"),
#         }

#         company_details = {
#             "name": data.get("company_details[name]"),
#             "website": data.get("company_details[website]"),
#             "overview": data.get("company_details[overview]"),
#         }

#         benefits = {
#             "offered": data.get("benefits[offered]"),
#         }

#         # Validation
#         if not job_details["position_title"] or (job_details["position_title"] == "add-new" and not job_details["position_title_new"]):
#             errors["position_title"] = "Position title is required."
#         if not job_details["job_description"]:
#             errors["job_description"] = "Job description is required."
#         if not requirements["threshold"].isdigit() or int(requirements["threshold"]) < 0 or int(requirements["threshold"]) > 100:
#             errors["threshold"] = "Threshold must be between 0 and 100."
#         if not job_type["type"]:
#             errors["job_type"] = "Job type is required."
#         if not job_type["work_arrangement"]:
#             errors["work_arrangement"] = "Work arrangement is required."
#         if not job_type["openings"].isdigit() or int(job_type["openings"]) < 1:
#             errors["openings"] = "Number of openings must be at least 1."
#         if not compensation["min_salary"].isdigit() or int(compensation["min_salary"]) < 0:
#             errors["salary"] = "Salaries cannot be negative."
#         if not compensation["max_salary"].isdigit() or int(compensation["max_salary"]) < 0:
#             errors["salary"] = "Salaries cannot be negative."
#         if int(compensation["min_salary"]) > int(compensation["max_salary"]) and int(compensation["max_salary"]) != 0:
#             errors["salary"] = "Minimum salary cannot exceed maximum salary."
#         if not compensation["currency"]:
#             errors["currency"] = "Currency is required."
#         if job_type["work_arrangement"] in ["Hybrid", "Onsite"] and not compensation["location"]:
#             errors["location"] = "Location is required for Hybrid or Onsite arrangements."
#         if not company_details["name"]:
#             errors["company_name"] = "Company name is required."
#         if company_details["website"] and not re.match(r"^https?://", company_details["website"]):
#             errors["company_website"] = "Invalid URL format (e.g., https://example.com)."
#         if not additional_info["posting_status"]:
#             errors["posting_status"] = "Posting status is required."

#         if errors:
#             logger.error(f"Validation errors: {errors}")
#             return JsonResponse({"success": False, "errors": errors}, status=400)

#         # Convert string values to appropriate types
#         requirements["threshold"] = int(requirements["threshold"])
#         job_type["openings"] = int(job_type["openings"])
#         compensation["min_salary"] = int(compensation["min_salary"])
#         compensation["max_salary"] = int(compensation["max_salary"])

#         # Prepare document for MongoDB
#         job_document = {
#             "job_details": {
#                 "position_title": job_details["position_title_new"] if job_details["position_title"] == "add-new" else job_details["position_title"],
#                 "job_description": job_details["job_description"],
#             },
#             "requirements": requirements,
#             "experience": experience if experience else [],
#             "education": [edu | {"degree": edu["degree_new"] if edu["degree"] == "add-new" else edu["degree"]} for edu in education] if education else [],
#             "certifications": certifications if certifications else [],
#             "job_type": job_type,
#             "compensation": compensation,
#             "additional_info": additional_info,
#             "company_details": company_details,
#             "benefits": benefits,
#             "weights": weights,
#             "posted_by": request.user.id,  # Assuming user ID from authentication
#             "application_count": 0,  # Initialize to 0
#             "created_at": datetime.datetime.now(),
#             "updated_at": datetime.datetime.now(),
#         }

#         # Save to MongoDB
#         try:
#             result = jobs_collection.insert_one(job_document)
#             return JsonResponse({"success": True, "message": "Job posted successfully!", "job_id": str(result.inserted_id)})
#         except Exception as e:
#             logger.error(f"Failed to save to MongoDB: {str(e)}")
#             return JsonResponse({"success": False, "errors": {"general": "Failed to save job posting."}}, status=500)

#     # Handle GET request
#     return render(request, "employer/job_form.html")



# def hr_dashboard(request):
#     try:
#         candidates = list(settings.MONGO_DB[RESUMES_EVALUATION_COLLECTION].aggregate([
#             {
#                 "$lookup": {
#                     "from": APPLICATIONS_COLLECTION,
#                     "localField": "application_id",
#                     "foreignField": "_id",
#                     "as": "application"
#                 }
#             },
#             {"$unwind": "$application"}
#         ]))
#         jobs = list(settings.MONGO_DB[JOBS_COLLECTION].find().sort("created_at", -1))

#         for candidate in candidates:
#             candidate['id'] = str(candidate['_id'])
#             candidate['application']['_id'] = str(candidate['application']['_id'])
#             del candidate['_id']
#             del candidate['application']['_id']

#         for job in jobs:
#             job['id'] = str(job['_id'])
#             del job['_id']

#         return render(request, 'employer/dashboard.html', {
#             'candidates': candidates,
#             'jobs': jobs
#         })
#     except Exception as e:
#         logger.error(f"Error in hr_dashboard: {str(e)}", exc_info=True)
#         return render(request, 'employer/dashboard.html', {
#             'error': 'Error fetching data from database',
#             'candidates': [],
#             'jobs': []
#         })




def hr_dashboard(request):
    try:
        # Get candidates from MongoDB
        candidates = list(settings.MONGO_DB["resumes_evaluation"].find())
        
        # Get jobs posted by the current HR
        jobs = list(jobs_collection.find().sort("created_at", -1))
        
        # Convert ObjectId to string for JSON serialization
        for candidate in candidates:
            candidate['id'] = str(candidate['_id'])
            del candidate['_id']
            
        for job in jobs:
            job['id'] = str(job['_id'])
            del job['_id']
            
        return render(request, 'employer/dashboard.html', {
            'candidates': candidates,
            'jobs': jobs
        })
    except Exception as e:
        logger.error(f"Error in hr_dashboard: {str(e)}")
        return render(request, 'employer/dashboard.html', {
            'error': 'Error fetching data from database',
            'candidates': [],
            'jobs': []
        })
 

 
# Homepage view
 
def login_signup(request):
    return render(request, 'login_signup.html')
 



def job_detail(request, job_id):
    return render(request, 'job_detail.html')



# def job_edit(request, job_id):
#     job = jobs_collection.find_one({'_id': ObjectId(job_id)})
#     if not job:
#         return render(request, '404.html', status=404)
#     # Convert ObjectId to string
#     if '_id' in job:
#         job['_id'] = str(job['_id'])
#     # Ensure all fields exist and are the correct type
#     job.setdefault('job_type', {})
#     job['job_type'].setdefault('type', '')
#     job['job_type'].setdefault('work_arrangement', '')
#     job['job_type'].setdefault('openings', '')
#     job.setdefault('compensation', {})
#     job['compensation'].setdefault('min_salary', '')
#     job['compensation'].setdefault('max_salary', '')
#     job['compensation'].setdefault('currency', '')
#     job['compensation'].setdefault('location', '')
#     job.setdefault('experience', [])
#     job.setdefault('education', [])
#     job.setdefault('certifications', [])
#     job.setdefault('requirements', {})
#     job['requirements'].setdefault('technical_skills', [])
#     job['requirements'].setdefault('soft_skills', [])
#     job['requirements'].setdefault('threshold', 80)
#     job.setdefault('company_details', {})
#     job['company_details'].setdefault('name', '')
#     job['company_details'].setdefault('website', '')
#     job['company_details'].setdefault('overview', '')
#     job.setdefault('benefits', {})
#     job['benefits'].setdefault('offered', '')
#     job.setdefault('additional_info', {})
#     job['additional_info'].setdefault('contact_information', '')
#     job['additional_info'].setdefault('posting_status', 'Draft')
#     return render(request, "employer/job_form.html", {"job": job, "edit_mode": True, "job_id": job_id})



@mongo_login_required
@csrf_exempt
def job_edit(request, job_id):
    """Edit an existing job posting. Only the job's owner (posted_by) can edit."""
    try:
        # Fetch job
        job = settings.MONGO_DB[JOBS_COLLECTION].find_one({'_id': ObjectId(job_id)})
        if not job:
            logger.warning(f"Job not found: {job_id}")
            return render(request, '404.html', status=404)
        
        # Authorize user
        if job['posted_by'] != request.mongo_user['user_id']:
            logger.warning(f"Unauthorized edit attempt for job {job_id} by user {request.mongo_user['user_id']}")
            return render(request, '403.html', status=403)

        if request.method == "POST":
            data = request.POST
            errors = {}

            # Extract and validate data (aligned with job_postform_view)
            job_details = {
                "position_title": data.get("job_details[position_title]"),
                "position_title_new": data.get("job_details[position_title_new]", ""),
                "job_description": data.get("job_details[job_description]"),
            }

            requirements = {
                "technical_skills": [
                    {"name": skill, "min_years": int(data.get(f"requirements[technical_skills][{i}][min_years]", 0))}
                    for i, skill in enumerate(data.getlist("requirements[technical_skills][]"))
                    if skill.strip()
                ],
                "soft_skills": [skill for skill in data.getlist("requirements[soft_skills][]") if skill.strip()],
                "threshold": data.get("requirements[threshold]", "0"),
            }

            priorities = {
                "skills": data.get("weights[skills]", "Medium"),
                "experience": data.get("weights[experience]", "Medium"),
                "education": data.get("weights[education]", "Low"),
                "projects": data.get("weights[projects]", "Low"),
                "soft_skills": data.get("weights[soft_skills]", "None"),
                "additional_info": data.get("weights[additional_info]", "None"),
            }

            weights, weight_error = map_priorities_to_weights(priorities)
            if weight_error:
                errors["skills_priority"] = weight_error
                logger.error(f"Priority validation failed: {weight_error}")

            experience = []
            for i in range(100):
                role = data.get(f"experience[{i}][role]")
                if not role:
                    break
                experience.append({
                    "role": role,
                    "role_new": data.get(f"experience[{i}][role_new]", ""),
                    "years": int(data.get(f"experience[{i}][years]", "0")) or 0,
                })

            education = []
            for i in range(100):
                degree = data.get(f"education[{i}][degree]")
                if not degree:
                    break
                education.append({
                    "degree": degree,
                    "degree_new": data.get(f"education[{i}][degree_new]", ""),
                })

            certifications = []
            for i in range(100):
                name = data.get(f"certifications[{i}][name]")
                if not name:
                    break
                certifications.append({
                    "name": name,
                })

            job_type = {
                "type": data.get("job_type[type]"),
                "work_arrangement": data.get("job_type[work_arrangement]"),
                "openings": data.get("job_type[openings]", "1"),
            }

            compensation = {
                "min_salary": data.get("compensation[min_salary]", "0"),
                "max_salary": data.get("compensation[max_salary]", "0"),
                "currency": data.get("compensation[currency]"),
                "location": data.get("compensation[location]", ""),
            }

            additional_info = {
                "contact_information": data.get("additional_info[contact_information]"),
            }

            company_details = {
                "name": data.get("company_details[name]"),
                "website": data.get("company_details[website]"),
                "overview": data.get("company_details[overview]"),
            }

            benefits = {
                "offered": data.get("benefits[offered]"),
            }

            status = data.get("status", JOB_STATUS_DRAFT)
            application_deadline = data.get("application_deadline", "")

            # Validation
            if not job_details["position_title"] or (job_details["position_title"] == "add-new" and not job_details["position_title_new"]):
                errors["position_title"] = "Position title is required."
            if not job_details["job_description"]:
                errors["job_description"] = "Job description is required."
            if not requirements["technical_skills"]:
                errors["technical_skills"] = "At least one technical skill is required."
            if not requirements["threshold"].isdigit() or int(requirements["threshold"]) < 0 or int(requirements["threshold"]) > 100:
                errors["threshold"] = "Threshold must be between 0 and 100."
            if not job_type["type"]:
                errors["job_type"] = "Job type is required."
            if not job_type["work_arrangement"]:
                errors["work_arrangement"] = "Work arrangement is required."
            if not job_type["openings"].isdigit() or int(job_type["openings"]) < 1:
                errors["openings"] = "Number of openings must be at least 1."
            if not compensation["min_salary"].isdigit() or int(compensation["min_salary"]) < 0:
                errors["salary"] = "Minimum salary cannot be negative."
            if not compensation["max_salary"].isdigit() or int(compensation["max_salary"]) < 0:
                errors["salary"] = "Maximum salary cannot be negative."
            if int(compensation["min_salary"]) > int(compensation["max_salary"]) and int(compensation["max_salary"]) != 0:
                errors["salary"] = "Minimum salary cannot exceed maximum salary."
            if not compensation["currency"]:
                errors["currency"] = "Currency is required."
            if job_type["work_arrangement"] in ["Hybrid", "Onsite"] and not compensation["location"]:
                errors["location"] = "Location is required for Hybrid or Onsite arrangements."
            if not company_details["name"]:
                errors["company_name"] = "Company name is required."
            if company_details["website"] and not re.match(r"^https?://", company_details["website"]):
                errors["company_website"] = "Invalid URL format (e.g., https://example.com)."
            if status not in [JOB_STATUS_OPEN, JOB_STATUS_DRAFT, JOB_STATUS_CLOSED]:
                errors["status"] = "Invalid status."
            if application_deadline and not re.match(r"^\d{4}-\d{2}-\d{2}$", application_deadline):
                errors["application_deadline"] = "Invalid date format (YYYY-MM-DD)."

            if errors:
                logger.error(f"Validation errors: {errors}")
                return JsonResponse({"success": False, "errors": errors}, status=400)

            # Convert string values to appropriate types
            requirements["threshold"] = int(requirements["threshold"])
            job_type["openings"] = int(job_type["openings"])
            compensation["min_salary"] = int(compensation["min_salary"])
            compensation["max_salary"] = int(compensation["max_salary"])
            application_deadline = datetime.datetime.strptime(application_deadline, "%Y-%m-%d") if application_deadline else None

            # Prepare document for MongoDB
            job_document = {
                "job_details": {
                    "position_title": job_details["position_title_new"] if job_details["position_title"] == "add-new" else job_details["position_title"],
                    "job_description": job_details["job_description"],
                },
                "requirements": requirements,
                "experience": experience if experience else [],
                "education": [edu | {"degree": edu["degree_new"] if edu["degree"] == "add-new" else edu["degree"]} for edu in education] if education else [],
                "certifications": certifications if certifications else [],
                "job_type": job_type,
                "compensation": compensation,
                "additional_info": additional_info,
                "company_details": company_details,
                "benefits": benefits,
                "weights": weights,
                "posted_by": job['posted_by'],  # Retain original posted_by
                "application_count": job.get("application_count", 0),  # Retain existing count
                "status": status,
                "application_deadline": application_deadline,
                "created_at": job.get("created_at", datetime.datetime.now()),
                "updated_at": datetime.datetime.now(),
            }

            # Save to MongoDB
            try:
                settings.MONGO_DB[JOBS_COLLECTION].update_one(
                    {"_id": ObjectId(job_id)},
                    {"$set": job_document}
                )

                # Log user activity
                settings.MONGO_DB[USER_ACTIVITY_LOGS_COLLECTION].insert_one({
                    "user_id": request.mongo_user['user_id'],
                    "action": "job_edited",
                    "details": {
                        "job_id": job_id,
                        "position_title": job_document["job_details"]["position_title"],
                        "timestamp": datetime.datetime.now().isoformat(),
                    },
                    "created_at": datetime.datetime.now().isoformat(),
                })

                logger.info(f"Job updated successfully: {job_id} by user {request.mongo_user['user_id']}")
                return JsonResponse({"success": True, "message": "Job updated successfully!", "job_id": job_id})
            except Exception as e:
                logger.error(f"Failed to update job in MongoDB: {str(e)}", exc_info=True)
                return JsonResponse({"success": False, "errors": {"general": "Failed to update job."}}, status=500)

        # GET request: Prepopulate form
        job['id'] = str(job['_id'])
        job.setdefault('status', JOB_STATUS_DRAFT)
        job.setdefault('application_deadline', '')
        job.setdefault('job_type', {})
        job['job_type'].setdefault('type', '')
        job['job_type'].setdefault('work_arrangement', '')
        job['job_type'].setdefault('openings', '')
        job.setdefault('compensation', {})
        job['compensation'].setdefault('min_salary', '')
        job['compensation'].setdefault('max_salary', '')
        job['compensation'].setdefault('currency', '')
        job['compensation'].setdefault('location', '')
        job.setdefault('experience', [])
        job.setdefault('education', [])
        job.setdefault('certifications', [])
        job.setdefault('requirements', {})
        job['requirements'].setdefault('technical_skills', [])
        for skill in job['requirements']['technical_skills']:
            skill.setdefault('min_years', 0)
        job['requirements'].setdefault('soft_skills', [])
        job['requirements'].setdefault('threshold', 80)
        job.setdefault('company_details', {})
        job['company_details'].setdefault('name', '')
        job['company_details'].setdefault('website', '')
        job['company_details'].setdefault('overview', '')
        job.setdefault('benefits', {})
        job['benefits'].setdefault('offered', '')
        job.setdefault('additional_info', {})
        job['additional_info'].setdefault('contact_information', '')
        job.setdefault('weights', {
            "skills": 0.35,
            "experience": 0.20,
            "education": 0.10,
            "projects": 0.10,
            "soft_skills": 0.05,
            "additional_info": 0.05
        })
        return render(request, "employer/job_form.html", {"job": job, "edit_mode": True, "job_id": job_id})

    except Exception as e:
        logger.error(f"Error in job_edit for job {job_id}: {str(e)}", exc_info=True)
        return render(request, '500.html', status=500)



@csrf_exempt
def close_job(request, job_id):
    jobs_collection.update_one({'_id': ObjectId(job_id)}, {'$set': {'status': 'closed'}})
    return redirect(reverse('hr_dashboard'))


            

def job_delete(request, job_id):
    return render(request, 'job_delete.html')
 


def interview_filtered_candidates(request):
    return render(request, 'interview_filtered_candidates.html')












## original
# def hr_dashboard(request):
#     try:
#         # Get candidates from MongoDB
#         candidates = list(settings.MONGO_DB["resumes_evaluation"].find())
        
#         # Get jobs posted by the current HR
#         # jobs = list(jobs_collection.find().sort("created_at", -1))
#         jobs = list(jobs_collection.find({"posted_by": request.user.id}).sort("created_at", -1))
        
#         # Convert ObjectId to string for JSON serialization
#         for candidate in candidates:
#             candidate['id'] = str(candidate['_id'])
#             del candidate['_id']
            
#         for job in jobs:
#             job['id'] = str(job['_id'])
#             del job['_id']
            
#         return render(request, 'employer/dashboard.html', {
#             'candidates': candidates,
#             'jobs': jobs
#         })
#     except Exception as e:
#         logger.error(f"Error in hr_dashboard: {str(e)}")
#         return render(request, 'employer/dashboard.html', {
#             'error': 'Error fetching data from database',
#             'candidates': [],
#             'jobs': []
#         })
 








