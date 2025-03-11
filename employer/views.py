from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime


# Create your views here.

# Dashboard view
def dashboard(request):
    return render(request, 'dashboard.html')

# Homepage view
def job_post(request):
    return render(request, 'job_form.html')
    
# def job_posting(request):
#     return render(request, 'employer/job_form.html')


from django.shortcuts import render
from django.http import JsonResponse
import pymongo
from bson import ObjectId
import re
import datetime
from django.conf import settings

# MongoDB connection
# client = pymongo.MongoClient("mongodb://localhost:27017/")
# db = client["job_postings_db"]
# jobs_collection = db["jobs"]
jobs_collection = settings.MONGO_DB["jobs"]


def job_form_view(request):
    if request.method == "POST":
        data = request.POST
        errors = {}

        # Extract and validate data
        job_details = {
            "position_title": data.get("job_details[position_title]"),
            "position_title_new": data.get("job_details[position_title_new]", ""),
            "department": data.get("job_details[department]"),
            "department_new": data.get("job_details[department_new]", ""),
            "job_description": data.get("job_details[job_description]"),
        }

        requirements = {
            "technical_skills": data.getlist("requirements[technical_skills][]"),
            "soft_skills": data.getlist("requirements[soft_skills][]"),
            "threshold": int(data.get("requirements[threshold]", 0)),
        }

        experience = []
        for i in range(100):  # Arbitrary large number to capture all entries
            role = data.get(f"experience[{i}][role]")
            if not role:
                break
            experience.append({
                "role": role,
                "role_new": data.get(f"experience[{i}][role_new]", ""),
                "years": int(data.get(f"experience[{i}][years]", 0)) or 0,
                "industry": data.get(f"experience[{i}][industry]", ""),
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
                "issuer": data.get(f"certifications[{i}][issuer]", ""),
            })

        job_type = {
            "type": data.get("job_type[type]"),
            "work_arrangement": data.get("job_type[work_arrangement]"),
            "openings": int(data.get("job_type[openings]", 1)) or 1,
        }

        compensation = {
            "min_salary": int(data.get("compensation[min_salary]", 0)) or 0,
            "max_salary": int(data.get("compensation[max_salary]", 0)) or 0,
            "currency": data.get("compensation[currency]"),
            "location": data.get("compensation[location]", ""),
        }

        additional_info = {
            "start_date": data.get("additional_info[start_date]"),
            "contact_information": data.get("additional_info[contact_information]"),
            "posting_status": data.get("additional_info[posting_status]"),
        }

        company_details = {
            "name": data.get("company_details[name]"),
            "website": data.get("company_details[website]"),
            "overview": data.get("company_details[overview]"),
        }

        benefits = {
            "offered": data.get("benefits[offered]"),
        }

        # Validation
        if not job_details["position_title"] or (job_details["position_title"] == "add-new" and not job_details["position_title_new"]):
            errors["position_title"] = "Position title is required."
        if not job_details["department"] or (job_details["department"] == "add-new" and not job_details["department_new"]):
            errors["department"] = "Department is required."
        if not job_details["job_description"]:
            errors["job_description"] = "Job description is required."
        if requirements["threshold"] < 0 or requirements["threshold"] > 100:
            errors["threshold"] = "Threshold must be between 0 and 100."
        if not job_type["type"]:
            errors["job_type"] = "Job type is required."
        if not job_type["work_arrangement"]:
            errors["work_arrangement"] = "Work arrangement is required."
        if job_type["openings"] < 1:
            errors["openings"] = "Number of openings must be at least 1."
        if compensation["min_salary"] < 0 or compensation["max_salary"] < 0:
            errors["salary"] = "Salaries cannot be negative."
        if compensation["min_salary"] > compensation["max_salary"]:
            errors["salary"] = "Minimum salary cannot exceed maximum salary."
        if not compensation["currency"]:
            errors["currency"] = "Currency is required."
        if job_type["work_arrangement"] in ["Hybrid", "Onsite"] and not compensation["location"]:
            errors["location"] = "Location is required for Hybrid or Onsite arrangements."
        if not company_details["name"]:
            errors["company_name"] = "Company name is required."
        if company_details["website"] and not re.match(r"^https?://", company_details["website"]):
            errors["company_website"] = "Invalid URL format (e.g., https://example.com)."
        if not additional_info["posting_status"]:
            errors["posting_status"] = "Posting status is required."

        # If there are errors, return them
        if errors:
            return JsonResponse({"success": False, "errors": errors}, status=400)

        # Prepare document for MongoDB
        job_document = {
            "job_details": {
                "position_title": job_details["position_title_new"] if job_details["position_title"] == "add-new" else job_details["position_title"],
                "department": job_details["department_new"] if job_details["department"] == "add-new" else job_details["department"],
                "job_description": job_details["job_description"],
            },
            "requirements": requirements,
            "experience": experience,
            "education": [edu | {"degree": edu["degree_new"] if edu["degree"] == "add-new" else edu["degree"]} for edu in education],
            "certifications": certifications,
            "job_type": job_type,
            "compensation": compensation,
            "additional_info": additional_info,
            "company_details": company_details,
            "benefits": benefits,
            "created_at": datetime.datetime.now(),
        }

        # Save to MongoDB
        result = jobs_collection.insert_one(job_document)
        return JsonResponse({"success": True, "message": "Job posted successfully!", "job_id": str(result.inserted_id)})

    # GET request: Render the form
    return render(request, "employer/job_form.html")














def hr_dashboard(request):
    return render(request, 'employer/dashboard.html')

def login_signup(request):
    return render(request, 'login_signup.html')



def job_listing(request):
    return render(request, 'job_listing.html')

def job_detail(request, job_id):
    return render(request, 'job_detail.html')

def job_edit(request, job_id):
    return render(request, 'job_edit.html')

def job_delete(request, job_id):
    return render(request, 'job_delete.html')

def candidate_listing(request):
    return render(request, 'employer\candidate_listing.html')


def candidates_per_job(request, job_id):
    return render(request, 'candidates_per_job.html')

def interview_filtered_candidates(request):
    return render(request, 'interview_filtered_candidates.html')

def hr_review(request):
    return render(request, 'hr_review.html')

def resume_analysis(request):
    return render(request, 'resume_analysis.html')

def candidate_comparison(request):
    return render(request, 'candidate_comparison.html')

def criteria_config(request):
    return render(request, 'criteria_config.html')

def video_call(request):
    return render(request, 'video_call.html')

def interview_scheduling(request):
    return render(request, 'interview_scheduling.html')

def job_analytics(request):
    return render(request, 'job_analytics.html')

def bulk_action(request):
    return render(request, 'bulk_action.html')

def report_viewing(request, report_id):
    return render(request, 'report_viewing.html')

def notification_settings(request):
    return render(request, 'notification_settings.html')

def profile(request):
    return render(request, 'hr_profile.html')