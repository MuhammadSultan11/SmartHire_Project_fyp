# # original code
from datetime import datetime
from pymongo import ReturnDocument
import json
from time import sleep
import uuid
from django.shortcuts import redirect, render
from django.conf import settings

from candidate.tasks import process_resume_task
from .forms import PDFUploadForm
from accounts.accounts_views import mongo_login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
import os
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import re
import ast  # For safely evaluating strings to Python objects
from django.shortcuts import render, redirect
from celery.result import AsyncResult
from django.views.decorators.http import require_http_methods
# from bson.objectid import ObjectId  # For converting MongoDB ObjectId to string
from bson import ObjectId
from .evocde import test_evaluations



logger = logging.getLogger(__name__)

USERS_COLLECTION = settings.USERS_COLLECTION
SESSIONS_COLLECTION = settings.MONGO_DB['sessions']

 
def serialize_mongo_document(doc):
    if doc is None:
        return {}
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

@mongo_login_required
def process_resume(request, pdf_id):
    def generate_progress():
        stages = [
            ("scanning", "Scanning Document", 25),
            ("extracting", "Extracting Text", 50),
            ("analyzing", "Analyzing Content", 75),
            ("preparing", "Preparing Form", 100)
        ]
        try:
            uploaded_pdf = settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})
            if not uploaded_pdf:
                logger.error(f"No resume found for pdf_id: {pdf_id}")
                yield f"data: {json.dumps({'error': 'The requested PDF does not exist.'})}\n\n"
                return

            pdf_path = uploaded_pdf['path']
            processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': pdf_id})
            # processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
            if processed_data:
                yield f"data: {json.dumps({'complete': True, 'resume_id': pdf_id})}\n\n"
                return

            task = process_resume_task.delay(pdf_path, pdf_id)
            print(f"Started processing task for pdf_id: {pdf_id}, Task ID: {task.id}")

            for stage, message, progress in stages:
                yield f"data: {json.dumps({'stage': stage, 'progress': progress, 'message': message})}\n\n"
                sleep(1)

            yield f"data: {json.dumps({'complete': True, 'resume_id': pdf_id})}\n\n"
        except Exception as e:
            logger.error(f"Error in process_resume: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    if request.headers.get('Accept') == 'text/event-stream':
        return StreamingHttpResponse(generate_progress(), content_type='text/event-stream')

    # processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': pdf_id})
    processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
    if processed_data:
        return render(request, 'candidate/resume_form.html', {'resume': processed_data['resume_data'], 'pdf_id': pdf_id})
    else:
        uploaded_pdf = settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})
        if not uploaded_pdf:
            return render(request, 'candidate/error.html', {'message': "The requested PDF does not exist."})
        task = process_resume_task.delay(uploaded_pdf['path'], pdf_id)
        return render(request, 'candidate/processing.html', {'task_id': task.id, 'pdf_id': pdf_id})

def task_status(request, task_id):
    try:
        task_result = AsyncResult(task_id)
        if task_result.state == 'PROGRESS':
            return JsonResponse({'state': 'PROGRESS', 'info': task_result.info})
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            return JsonResponse({'state': 'SUCCESS', 'resume_id': result['pdf_id']})
        elif task_result.state == 'FAILURE':
            return JsonResponse({'state': 'FAILURE', 'error': str(task_result.result)})
        return JsonResponse({'state': task_result.state})
    except Exception as e:
        logger.error(f"Error in task_status for task_id {task_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


# original code 
@require_POST
@mongo_login_required
def apply_job(request):
    try:
        user_id = request.mongo_user['user_id']
        print(f"Session data: {request.session.items()}, Mongo user: {request.mongo_user}, POST data: {request.POST}, FILES: {request.FILES}")

        job_id = request.POST.get('job_id')

        # Fetch the job document to get the posted_by field
        job_doc = settings.MONGO_DB['jobs'].find_one({'_id': ObjectId(job_id)})
        posted_by = job_doc.get('posted_by') if job_doc else None
        print(f"Job {job_id} posted_by: {posted_by}")


        resume_id = request.POST.get('resume_id')

        if 'resume' in request.FILES:
            # New resume upload
            resume_file = request.FILES['resume']
            if not job_id:
                logger.warning("No job_id provided in request")
                return JsonResponse({'success': False, 'error': 'Job ID is required'}, status=400)

            resume_id = str(uuid.uuid4())
            resume_dir = os.path.join('resumes', user_id)
            resume_path = os.path.join(resume_dir, resume_file.name)

            os.makedirs(resume_dir, exist_ok=True)
            with open(resume_path, 'wb+') as destination:
                for chunk in resume_file.chunks():
                    destination.write(chunk)

            settings.MONGO_DB['resumes'].insert_one({
                '_id': resume_id,
                'user_id': user_id,
                'path': resume_path,
                'name': resume_file.name,
                'uploaded_at': datetime.now()
            })

            task = process_resume_task.delay(resume_path, resume_id)

            # settings.MONGO_DB['applications'].insert_one({
            settings.MONGO_DB['temp_applications'].insert_one({
                'user_id': user_id,
                'job_id': job_id,
                'posted_by': posted_by,  # Add posted_by field
                'resume_id': resume_id,
                'applied_at': datetime.now()
            })

            print(f"Application submitted with new resume: User {user_id}, Job {job_id}, Resume {resume_id}, Task {task.id}")
            return JsonResponse({'success': True, 'resume_id': resume_id, 'task_id': task.id})

        elif resume_id and resume_id != 'undefined':
            # Existing resume selected
            if not job_id:
                logger.warning(f"Missing job_id: job_id={job_id}")
                return JsonResponse({'success': False, 'error': 'Job ID is required'}, status=400)

            resume = settings.MONGO_DB['resumes'].find_one({'_id': resume_id})
            if not resume:
                logger.warning(f"Resume not found: {resume_id}")
                return JsonResponse({'success': False, 'error': 'Resume not found'}, status=404)
                
            # Check if processed data exists
            processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': resume_id})
            processed_resume_id = str(processed_data['_id']) if processed_data and '_id' in processed_data else None

            # settings.MONGO_DB['applications'].insert_one({
            settings.MONGO_DB['temp_applications'].insert_one({
                'user_id': user_id,
                'job_id': job_id,
                'posted_by': posted_by,  # Add posted_by field
                'resume_id': resume_id,
                'processed_resume_id':processed_resume_id,
                'applied_at': datetime.now()
            })

            if processed_data:
                # Use existing processed data
                print(f"Application submitted with existing processed resume: User {user_id}, Job {job_id}, Resume {resume_id}")
                return JsonResponse({'success': True, 'resume_id': resume_id})  # No task_id needed
            else:
                # Process the resume if not already processed
                task = process_resume_task.delay(resume['path'], resume_id)
                print(f"Application submitted with existing unprocessed resume: User {user_id}, Job {job_id}, Resume {resume_id}, Task {task.id}")
                return JsonResponse({'success': True, 'resume_id': resume_id, 'task_id': task.id})

        logger.warning(f"No valid resume provided in request: resume_id={resume_id}, FILES={request.FILES}")
        return JsonResponse({'success': False, 'error': 'No resume provided'}, status=400)

    except Exception as e:
        logger.error(f"Error in apply_job: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@mongo_login_required
def get_resumes(request):
    try:
        resumes = list(settings.MONGO_DB['resumes'].find({'user_id': str(request.mongo_user['user_id'])}))
        resume_list = []
        for resume in resumes:
            resume_list.append({
                'id': str(resume['_id']),
                'name': resume['name'],
                'uploaded_at': resume['uploaded_at'].isoformat()
            })
        print(f"Resumes fetched for user: {request.mongo_user['user_id']}")
        return JsonResponse({'success': True, 'resumes': resume_list})
    except Exception as e:
        logger.error(f"Error in get_resumes: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@require_POST
@mongo_login_required
def submit_resume(request):
    try:
        user_id = str(request.mongo_user['user_id'])
        pdf_id = request.POST.get('pdf_id', '')
        if not pdf_id:
            logger.warning(f"No pdf_id provided for user_id: {user_id}")
            return render(request, 'candidate/resume_form.html', {'error': 'PDF ID is required'})

        # Fetch existing processed resume data from MongoDB
        processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
        existing_resume_data = processed_data.get('resume_data', {}) if processed_data else {}

        # Extract form data
        resume_data = {
            'Personal_Information': {
                'Name': request.POST.get('Personal_Information[Name]', '').strip(),
                'Role': request.POST.get('Personal_Information[Role]', '').strip(),
                'Email': request.POST.get('Personal_Information[Email]', '').strip(),
                'Phone_number': request.POST.get('Personal_Information[Phone_number]', '').strip(),
                'LinkedIn': request.POST.get('Personal_Information[LinkedIn]', '').strip()
            },
            'Professional_Summary': request.POST.get('Professional_Summary', '').strip(),
            'Skills': [],
            'Experience': [],
            'Education': [],
            'Projects': [],
            'Additional_Information': request.POST.get('Additional_Information', '').strip()
        }

        # Validate Name
        if not resume_data['Personal_Information']['Name']:
            logger.warning(f"Invalid Name field for user_id: {user_id}")
            return render(request, 'candidate/resume_form.html', {'resume': resume_data, 'error': 'Name is required'})

        # Validate LinkedIn URL
        linkedin = resume_data['Personal_Information']['LinkedIn']
        if linkedin and not re.match(r'^(https?:\/\/)?([\w\d-]+\.)+[\w\d-]+(\/.*)?$', linkedin):
            logger.warning(f"Invalid LinkedIn URL: {linkedin}")
            return render(request, 'candidate/resume_form.html', {'resume': resume_data, 'error': 'Invalid LinkedIn URL'})

        # Process Skills
        skills_input = request.POST.get('Skills', '').strip()
        if skills_input:
            try:
                if skills_input.startswith('[') and skills_input.endswith(']'):
                    skills_list = ast.literal_eval(skills_input)
                    resume_data['Skills'] = [
                        s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
                        for s in skills_list if s and isinstance(s, (str, dict))
                    ]
                else:
                    resume_data['Skills'] = [s.strip() for s in skills_input.split(',') if s.strip()]
            except (ValueError, SyntaxError):
                resume_data['Skills'] = [s.strip() for s in skills_input.split(',') if s.strip()]

        # Process Experience
        for key in request.POST:
            if key.startswith('Experience['):
                idx = int(key.split('[')[1].split(']')[0])
                while len(resume_data['Experience']) <= idx:
                    resume_data['Experience'].append({})
                if 'Job_Title' in key:
                    resume_data['Experience'][idx]['Job_Title'] = request.POST[key].strip()
                elif 'Company_Name' in key:
                    resume_data['Experience'][idx]['Company_Name'] = request.POST[key].strip()
                elif 'Dates_Duration' in key:
                    resume_data['Experience'][idx]['Dates_Duration'] = request.POST[key].strip()
                elif 'Job_Description' in key:
                    resume_data['Experience'][idx]['Job_Description'] = request.POST[key].strip()

        # Process Education
        for key in request.POST:
            if key.startswith('Education['):
                idx = int(key.split('[')[1].split(']')[0])
                while len(resume_data['Education']) <= idx:
                    resume_data['Education'].append({})
                if 'Degree' in key:
                    resume_data['Education'][idx]['Degree'] = request.POST[key].strip()
                elif 'Institution' in key:
                    resume_data['Education'][idx]['Institution'] = request.POST[key].strip()
                elif 'Dates' in key:
                    resume_data['Education'][idx]['Dates'] = request.POST[key].strip()

        # Process Projects
        for key in request.POST:
            if key.startswith('Projects['):
                idx = int(key.split('[')[1].split(']')[0])
                while len(resume_data['Projects']) <= idx:
                    resume_data['Projects'].append({})
                if 'Name' in key:
                    resume_data['Projects'][idx]['Name'] = request.POST[key].strip()
                elif 'Description' in key:
                    resume_data['Projects'][idx]['Description'] = request.POST[key].strip()

        # Merge with existing OCR-parsed data
        merged_resume_data = existing_resume_data.copy()
        merged_resume_data.update(resume_data)

        # Clean Skills in merged data
        if isinstance(merged_resume_data.get('Skills'), str):
            try:
                skills_list = ast.literal_eval(merged_resume_data['Skills']) if merged_resume_data['Skills'].startswith('[') else merged_resume_data['Skills'].split(',')
                merged_resume_data['Skills'] = [
                    s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
                    for s in skills_list if s and isinstance(s, (str, dict))
                ]
            except (ValueError, SyntaxError):
                logger.warning(f"Failed to parse Skills: {merged_resume_data['Skills']}")
                merged_resume_data['Skills'] = resume_data['Skills']
        elif isinstance(merged_resume_data.get('Skills'), list):
            merged_resume_data['Skills'] = [
                s.get('skill', s).strip() if isinstance(s, dict) else s.strip()
                for s in merged_resume_data['Skills'] if s and isinstance(s, (str, dict))
            ]
        else:
            merged_resume_data['Skills'] = resume_data['Skills']

        # Ensure all template sections
        template_sections = ['Personal_Information', 'Professional_Summary', 'Experience', 'Education', 
                            'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information']
        for section in template_sections:
            if section not in merged_resume_data:
                merged_resume_data[section] = [] if section in ['Experience', 'Education', 'Projects', 'Certifications_and_Licenses', 'References'] else ''

        # Find temp application
        temp_application = settings.MONGO_DB['temp_applications'].find_one({
            'user_id': user_id,
            'resume_id': pdf_id
        })
        job_id = temp_application['job_id'] if temp_application else None
        if not job_id:
            logger.error(f"No job_id found for user_id: {user_id}, pdf_id: {pdf_id}")
            return render(request, 'candidate/error.html', {'message': 'Job ID is missing'})

        # Validate job_id
        try:
            job_id_obj = ObjectId(job_id)
        except Exception as e:
            logger.error(f"Invalid job_id: {job_id}, Error: {str(e)}")
            return render(request, 'candidate/error.html', {'message': 'Invalid job ID'})

        # Fetch job document
        job_doc = settings.MONGO_DB['jobs'].find_one({'_id': job_id_obj})
        if not job_doc:
            logger.error(f"No job found for job_id: {job_id}")
            return render(request, 'candidate/error.html', {'message': 'Job not found'})
        posted_by = job_doc.get('posted_by')

        # Save processed resume
        resume_doc = settings.MONGO_DB['processed_resumes'].find_one_and_update(
            {'original_pdf_id': pdf_id, 'user_id': user_id},
            {
                '$set': {
                    'resume_data': merged_resume_data,
                    'processed_at': datetime.now(),
                    'user_id': user_id,
                    'original_pdf_id': pdf_id,
                    'is_final': True
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        processed_resume_id = str(resume_doc['_id'])
        logger.info(f"Final Resume saved for user {user_id}, pdf_id {pdf_id}, resume_id: {processed_resume_id}")

        # Insert application
        application_document = {
            'user_id': user_id,
            'job_id': str(job_id_obj),
            'posted_by': posted_by,
            'processed_resume_id': processed_resume_id,
            'resume_id': pdf_id,
            'applied_at': temp_application.get('applied_at', datetime.now()),
            'status': 'submitted',
            'application_data': {
                'submission_method': 'manual_edit',
                'submitted_at': datetime.now()
            }
        }
        result = settings.MONGO_DB['applications'].insert_one(application_document)
        application_id = str(result.inserted_id)
        logger.info(f"Inserted application with ID: {application_id}")

        # Update job application count
        settings.MONGO_DB['jobs'].update_one(
            {"_id": job_id_obj},
            {"$inc": {"application_count": 1}}
        )

        # Fetch job and resume for evaluation
        job_data = {
            "_id": {"$oid": str(job_doc["_id"])},
            "job_details": job_doc.get("job_details", {}),
            "requirements": job_doc.get("requirements", {}),
            "experience": job_doc.get("experience", []),
            "education": job_doc.get("education", []),
            "weights": job_doc.get("weights", {})
        }
        resume = settings.MONGO_DB['processed_resumes'].find_one({"_id": ObjectId(processed_resume_id)})
        if not resume:
            logger.error(f"No resume found with _id: {processed_resume_id}")
            return render(request, 'candidate/error.html', {'message': 'Resume not found'})

        resume_data = resume.get('resume_data', {})
        if not isinstance(resume_data, dict):
            logger.error(f"Invalid resume_data format for resume_id: {processed_resume_id}")
            return render(request, 'candidate/error.html', {'message': 'Invalid resume data'})
            # Run evaluation
        try:
            test_evaluations(resume_data, job_data, user_id, application_id, posted_by)
        except Exception as eval_exc:
            logger.error(f"Error in test_evaluations: {str(eval_exc)}", exc_info=True)


        # Clean up temp application
        # settings.MONGO_DB['temp_applications'].delete_one({'_id': temp_application['_id']})

        return HttpResponseRedirect('/candidate/profile/')
    except Exception as e:
        logger.error(f"Error in submit_resume: {str(e)}", exc_info=True)
        return render(request, 'candidate/error.html', {'message': str(e)})




















def candidate_profile(request):
    user_id = request.session.get('user_id', 'default_user')
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    
    default_data = {
        "user_id": user_id,
        "name": "John Doe",
        "title": "Software Engineer | AI Enthusiast",
        "location": "Lahore, Pakistan",
        "about": "A passionate developer with 5+ years in web and AI technologies.",
        "social_links": ["https://github.com/johndoe", "https://linkedin.com/in/johndoe"],
        "profile_picture": "https://placehold.co/150x150",
        "experiences": [],
        "educations": [],
        "certifications": [],
        "projects": [],
        "skills": []
    }
    
    profile_data = {**default_data, **user_data}
    return render(request, 'candidate/profile.html', {
        "profile": profile_data,
        "experiences": profile_data.get("experiences", []),
        "educations": profile_data.get("educations", []),
        "certifications": profile_data.get("certifications", []),
        "projects": profile_data.get("projects", []),
        "skills": profile_data.get("skills", [])
    })

@csrf_exempt
def api_profile(request):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        data = json.loads(request.body)
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": data.get("name"),
                "title": data.get("title"),
                "location": data.get("location"),
                "about": data.get("about"),
                "social_links": data.get("social_links")
            }},
            upsert=True
        )
        return JsonResponse({"status": "success"})
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    return JsonResponse(user_data)


@csrf_exempt
def api_profile_picture(request):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        if 'profile_picture' not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        file = request.FILES['profile_picture']
        # Generate a unique filename
        filename = f"{uuid.uuid4()}_{file.name}"
        # Define the save path
        save_path = os.path.join(settings.MEDIA_ROOT, 'profile_pictures', filename)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Save the file
        with open(save_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        file_url = os.path.join(settings.MEDIA_URL, 'profile_pictures', filename).replace('\\', '/')
        # Construct the URL for the saved file
        # file_url = f"{settings.MEDIA_URL}profile_pictures/{filename}"

        # Update MongoDB with the file URL
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$set": {"profile_picture": file_url}},
            upsert=True
        )

        return JsonResponse({"status": "success", "profile_picture": file_url})

    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
def api_experience(request, item_id=None):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        data = json.loads(request.body)
        experience = {
            "id": str(uuid.uuid4()),
            "title": data.get("title"),
            "company": data.get("company"),
            "location": data.get("location"),
            "employment_type": data.get("employment_type"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "description": data.get("description"),
            "skills": data.get("skills", [])
        }
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$push": {"experiences": experience}},
            upsert=True
        )
        return JsonResponse({"status": "success", "id": experience["id"]})
    elif request.method == 'PUT' and item_id:
        data = json.loads(request.body)
        data["id"] = item_id
        USERS_COLLECTION.update_one(
            {"user_id": user_id, "experiences.id": item_id},
            {"$set": {"experiences.$": data}}
        )
        return JsonResponse({"status": "success"})
    elif request.method == 'DELETE' and item_id:
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$pull": {"experiences": {"id": item_id}}}
        )
        return JsonResponse({"status": "success"})
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    return JsonResponse({"experiences": user_data.get("experiences", [])})

@csrf_exempt
def api_education(request, item_id=None):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        data = json.loads(request.body)
        education = {
            "id": str(uuid.uuid4()),
            "school": data.get("school"),
            "degree": data.get("degree"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "grade": data.get("grade")
        }
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$push": {"educations": education}},
            upsert=True
        )
        return JsonResponse({"status": "success", "id": education["id"]})
    elif request.method == 'PUT' and item_id:
        data = json.loads(request.body)
        data["id"] = item_id
        USERS_COLLECTION.update_one(
            {"user_id": user_id, "educations.id": item_id},
            {"$set": {"educations.$": data}}
        )
        return JsonResponse({"status": "success"})
    elif request.method == 'DELETE' and item_id:
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$pull": {"educations": {"id": item_id}}}
        )
        return JsonResponse({"status": "success"})
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    return JsonResponse({"educations": user_data.get("educations", [])})

@csrf_exempt
def api_certification(request, item_id=None):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        data = json.loads(request.body)
        certification = {
            "id": str(uuid.uuid4()),
            "name": data.get("name"),
            "issuer": data.get("issuer"),
            "issue_date": data.get("issue_date"),
            "expiration_date": data.get("expiration_date"),
            "credential_id": data.get("id")  # Renamed to avoid confusion with item ID
        }
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$push": {"certifications": certification}},
            upsert=True
        )
        return JsonResponse({"status": "success", "id": certification["id"]})
    elif request.method == 'PUT' and item_id:
        data = json.loads(request.body)
        data["id"] = item_id
        USERS_COLLECTION.update_one(
            {"user_id": user_id, "certifications.id": item_id},
            {"$set": {"certifications.$": data}}
        )
        return JsonResponse({"status": "success"})
    elif request.method == 'DELETE' and item_id:
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$pull": {"certifications": {"id": item_id}}}
        )
        return JsonResponse({"status": "success"})
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    return JsonResponse({"certifications": user_data.get("certifications", [])})

@csrf_exempt
def api_project(request, item_id=None):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        data = json.loads(request.body)
        project = {
            "id": str(uuid.uuid4()),
            "title": data.get("title"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "description": data.get("description"),
            "url": data.get("url")
        }
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$push": {"projects": project}},
            upsert=True
        )
        return JsonResponse({"status": "success", "id": project["id"]})
    elif request.method == 'PUT' and item_id:
        data = json.loads(request.body)
        data["id"] = item_id
        USERS_COLLECTION.update_one(
            {"user_id": user_id, "projects.id": item_id},
            {"$set": {"projects.$": data}}
        )
        return JsonResponse({"status": "success"})
    elif request.method == 'DELETE' and item_id:
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$pull": {"projects": {"id": item_id}}}
        )
        return JsonResponse({"status": "success"})
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    return JsonResponse({"projects": user_data.get("projects", [])})

@csrf_exempt
def api_skill(request, item_id=None):
    user_id = request.session.get('user_id', 'default_user')
    if request.method == 'POST':
        data = json.loads(request.body)
        skill = {
            "id": str(uuid.uuid4()),
            "name": data.get("name"),
            "category": data.get("category"),
            "level": data.get("level")
        }


        # skill = {"id": str(uuid.uuid4()), "name": data.get("name")}
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$push": {"skills": skill}},
            upsert=True
        )
        return JsonResponse({"status": "success", "id": skill["id"]})
    elif request.method == 'PUT' and item_id:
        data = json.loads(request.body)
        data["id"] = item_id
        USERS_COLLECTION.update_one(
            {"user_id": user_id, "skills.id": item_id},
            {"$set": {"skills.$": data}}
        )
        return JsonResponse({"status": "success"})
    elif request.method == 'DELETE' and item_id:
        USERS_COLLECTION.update_one(
            {"user_id": user_id},
            {"$pull": {"skills": {"id": item_id}}}
        )
        return JsonResponse({"status": "success"})
    user_data = serialize_mongo_document(USERS_COLLECTION.find_one({"user_id": user_id}))
    return JsonResponse({"skills": user_data.get("skills", [])})




# def upload_pdf(request):
#     if request.method == 'POST':
#         form = PDFUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             uploaded_pdf = form.save()
#             return redirect('process_resume', pdf_id=uploaded_pdf.id)
#     else:
#         form = PDFUploadForm()
#     return render(request, 'upload_pdf.html', {'form': form})





# def extract_section(cv_text, section_name):
#     # Update the regex to adapt to the actual string formatting
#     pattern = re.compile(rf"'{section_name}':\s*(\[[^]]*\]|{{[^}}]*}}|'.*?')", re.DOTALL)

#     match = pattern.search(cv_text)
#     result = ''
#     if match:
#         return match.group(1).strip()
#     return f"Section '{section_name}' not found."


# def resume_form(request, resume_data=None):
#     if resume_data is None:
#         resume_data = {}  # Default empty dictionary if no data provided

#     if "Experience" in resume_data and "Contextual_Career_Experience" in resume_data:
#         resume_data["Experience"] += resume_data["Contextual_Career_Experience"]
#         del resume_data["Contextual_Career_Experience"]
    
#     return render(request, 'candidate/resume_form.html', context={'resume': resume_data})
 
  

