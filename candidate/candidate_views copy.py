# from datetime import datetime
# import json
# from time import sleep
# import uuid
# from django.shortcuts import redirect, render
# from django.conf import settings
# from candidate.tasks import process_resume_task, evaluate_resume_task
# from .forms import PDFUploadForm
# from accounts.accounts_views import mongo_login_required
# from django.http import JsonResponse, StreamingHttpResponse
# from django.views.decorators.http import require_POST
# import os
# import logging
# from django.shortcuts import render
# from django.http import JsonResponse, HttpResponseRedirect
# from django.views.decorators.csrf import csrf_exempt
# import re
# import ast
# from django.shortcuts import render, redirect
# from celery.result import AsyncResult
# from django.views.decorators.http import require_http_methods
# logger = logging.getLogger(__name__)

# USERS_COLLECTION = settings.USERS_COLLECTION
# SESSIONS_COLLECTION = settings.MONGO_DB['sessions']

# def serialize_mongo_document(doc):
#     if doc is None:
#         return {}
#     if '_id' in doc:
#         doc['_id'] = str(doc['_id'])
#     return doc

# @mongo_login_required
# def process_resume(request, pdf_id):
#     def generate_progress():
#         stages = [
#             ("scanning", "Scanning Document", 25),
#             ("extracting", "Extracting Text", 50),
#             ("analyzing", "Analyzing Content", 75),
#             ("preparing", "Preparing Form", 100)
#         ]
#         try:
#             uploaded_pdf = settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})
#             if not uploaded_pdf:
#                 logger.error(f"No resume found for pdf_id: {pdf_id}")
#                 yield f"data: {json.dumps({'error': 'The requested PDF does not exist.'})}\n\n"
#                 return

#             pdf_path = uploaded_pdf['path']
#             processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': pdf_id})
#             if processed_data:
#                 yield f"data: {json.dumps({'complete': True, 'resume_id': pdf_id})}\n\n"
#                 return

#             task = process_resume_task.delay(pdf_path, pdf_id)
#             print(f"Started processing task for pdf_id: {pdf_id}, Task ID: {task.id}")

#             for stage, message, progress in stages:
#                 yield f"data: {json.dumps({'stage': stage, 'progress': progress, 'message': message})}\n\n"
#                 sleep(1)

#             yield f"data: {json.dumps({'complete': True, 'resume_id': pdf_id})}\n\n"
#         except Exception as e:
#             logger.error(f"Error in process_resume: {str(e)}")
#             yield f"data: {json.dumps({'error': str(e)})}\n\n"

#     if request.headers.get('Accept') == 'text/event-stream':
#         return StreamingHttpResponse(generate_progress(), content_type='text/event-stream')

#     processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
#     if processed_data:
#         return render(request, 'candidate/resume_form.html', {'resume': processed_data['resume_data'], 'pdf_id': pdf_id})
#     else:
#         uploaded_pdf = settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})
#         if not uploaded_pdf:
#             return render(request, 'candidate/error.html', {'message': "The requested PDF does not exist."})
#         task = process_resume_task.delay(uploaded_pdf['path'], pdf_id)
#         return render(request, 'candidate/processing.html', {'task_id': task.id, 'pdf_id': pdf_id})

# def task_status(request, task_id):
#     try:
#         task_result = AsyncResult(task_id)
#         if task_result.state == 'PROGRESS':
#             return JsonResponse({'state': 'PROGRESS', 'info': task_result.info})
#         elif task_result.state == 'SUCCESS':
#             result = task_result.result
#             return JsonResponse({'state': 'SUCCESS', 'resume_id': result['pdf_id']})
#         elif task_result.state == 'FAILURE':
#             return JsonResponse({'state': 'FAILURE', 'error': str(task_result.result)})
#         return JsonResponse({'state': task_result.state})
#     except Exception as e:
#         logger.error(f"Error in task_status for task_id {task_id}: {str(e)}", exc_info=True)
#         return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

# @require_POST
# @mongo_login_required
# def apply_job(request):
#     try:
#         user_id = request.mongo_user['user_id']
#         print(f"Session data: {request.session.items()}, Mongo user: {request.mongo_user}, POST data: {request.POST}, FILES: {request.FILES}")

#         job_id = request.POST.get('job_id')
#         resume_id = request.POST.get('resume_id')

#         if 'resume' in request.FILES:
#             resume_file = request.FILES['resume']
#             if not job_id:
#                 logger.warning("No job_id provided in request")
#                 return JsonResponse({'success': False, 'error': 'Job ID is required'}, status=400)

#             resume_id = str(uuid.uuid4())
#             resume_dir = os.path.join('resumes', user_id)
#             resume_path = os.path.join(resume_dir, resume_file.name)

#             os.makedirs(resume_dir, exist_ok=True)
#             with open(resume_path, 'wb+') as destination:
#                 for chunk in resume_file.chunks():
#                     destination.write(chunk)

#             settings.MONGO_DB['resumes'].insert_one({
#                 '_id': resume_id,
#                 'user_id': user_id,
#                 'path': resume_path,
#                 'name': resume_file.name,
#                 'uploaded_at': datetime.now()
#             })

#             task = process_resume_task.delay(resume_path, resume_id)
#             settings.MONGO_DB['temp_applications'].insert_one({
#                 'user_id': user_id,
#                 'job_id': job_id,
#                 'resume_id': resume_id,
#                 'applied_at': datetime.now()
#             })

#             print(f"Application submitted with new resume: User {user_id}, Job {job_id}, Resume {resume_id}, Task {task.id}")
#             return JsonResponse({'success': True, 'resume_id': resume_id, 'task_id': task.id})

#         elif resume_id and resume_id != 'undefined':
#             if not job_id:
#                 logger.warning(f"Missing job_id: job_id={job_id}")
#                 return JsonResponse({'success': False, 'error': 'Job ID is required'}, status=400)

#             resume = settings.MONGO_DB['resumes'].find_one({'_id': resume_id})
#             if not resume:
#                 logger.warning(f"Resume not found: {resume_id}")
#                 return JsonResponse({'success': False, 'error': 'Resume not found'}, status=404)

#             processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': resume_id})
#             settings.MONGO_DB['temp_applications'].insert_one({
#                 'user_id': user_id,
#                 'job_id': job_id,
#                 'resume_id': resume_id,
#                 'applied_at': datetime.now()
#             })

#             if processed_data:
#                 print(f"Application submitted with existing processed resume: User {user_id}, Job {job_id}, Resume {resume_id}")
#                 return JsonResponse({'success': True, 'resume_id': resume_id})
#             else:
#                 task = process_resume_task.delay(resume['path'], resume_id)
#                 print(f"Application submitted with existing unprocessed resume: User {user_id}, Job {job_id}, Resume {resume_id}, Task {task.id}")
#                 return JsonResponse({'success': True, 'resume_id': resume_id, 'task_id': task.id})

#         logger.warning(f"No valid resume provided in request: resume_id={resume_id}, FILES={request.FILES}")
#         return JsonResponse({'success': False, 'error': 'No resume provided'}, status=400)

#     except Exception as e:
#         logger.error(f"Error in apply_job: {str(e)}", exc_info=True)
#         return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)

# @mongo_login_required
# def get_resumes(request):
#     try:
#         resumes = list(settings.MONGO_DB['resumes'].find({'user_id': str(request.mongo_user['user_id'])}))
#         resume_list = []
#         for resume in resumes:
#             resume_list.append({
#                 'id': str(resume['_id']),
#                 'name': resume['name'],
#                 'uploaded_at': resume['uploaded_at'].isoformat()
#             })
#         print(f"Resumes fetched for user: {request.mongo_user['user_id']}")
#         return JsonResponse({'success': True, 'resumes': resume_list})
#     except Exception as e:
#         logger.error(f"Error in get_resumes: {str(e)}")
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)




# @require_POST
# @mongo_login_required
# def submit_resume(request):
#     try:
#         user_id = str(request.mongo_user['user_id'])
#         pdf_id = request.POST.get('pdf_id', '')

#         if not pdf_id:
#             logger.error("No pdf_id provided in request")
#             return render(request, 'candidate/error.html', {'message': "PDF ID is required"})

#         # Fetch existing processed resume data
#         processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
#         existing_resume_data = processed_data.get('resume_data', {}) if processed_data else {}

#         # Initialize resume data from form
#         resume_data = {
#             'Personal_Information': {
#                 'Name': request.POST.get('Personal_Information[Name]', ''),
#                 'Role': request.POST.get('Personal_Information[Role]', ''),
#                 'Email': request.POST.get('Personal_Information[Email]', ''),
#                 'Phone_number': request.POST.get('Personal_Information[Phone_number]', ''),
#                 'LinkedIn': request.POST.get('Personal_Information[LinkedIn]', '')
#             },
#             'Professional_Summary': request.POST.get('Professional_Summary', ''),
#             'Skills': request.POST.get('Skills', ''),
#             'Experience': [],
#             'Education': [],
#             'Projects': [],
#             'Additional_Information': request.POST.get('Additional_Information', ''),
#             'Certifications_and_Licenses': [],
#             'References': []
#         }

#         # Validate LinkedIn URL
#         linkedin = resume_data['Personal_Information']['LinkedIn']
#         if linkedin and not re.match(r'^(https?:\/\/)?([\w\d-]+\.)+[\w\d-]+(\/.*)?$', linkedin):
#             logger.warning(f"Invalid LinkedIn URL: {linkedin}")
#             return render(request, 'candidate/resume_form.html', {'resume': resume_data, 'error': 'Invalid LinkedIn URL'})

#         # Process Experience
#         for key in request.POST:
#             if key.startswith('Experience['):
#                 try:
#                     idx = int(key.split('[')[1].split(']')[0])
#                     while len(resume_data['Experience']) <= idx:
#                         resume_data['Experience'].append({})
#                     if 'Job_Title' in key:
#                         resume_data['Experience'][idx]['Job_Title'] = request.POST[key]
#                     elif 'Company_Name' in key:
#                         resume_data['Experience'][idx]['Company_Name'] = request.POST[key]
#                     elif 'Dates_Duration' in key:
#                         resume_data['Experience'][idx]['Dates_Duration'] = request.POST[key]
#                     elif 'Job_Description' in key:
#                         resume_data['Experience'][idx]['Job_Description'] = request.POST[key]
#                 except (ValueError, IndexError) as e:
#                     logger.warning(f"Invalid Experience key format: {key}, error: {str(e)}")
#                     continue

#         # Process Education
#         for key in request.POST:
#             if key.startswith('Education['):
#                 try:
#                     idx = int(key.split('[')[1].split(']')[0])
#                     while len(resume_data['Education']) <= idx:
#                         resume_data['Education'].append({})
#                     if 'Degree' in key:
#                         resume_data['Education'][idx]['Degree'] = request.POST[key]
#                     elif 'Institution' in key:
#                         resume_data['Education'][idx]['Institution'] = request.POST[key]
#                     elif 'Dates' in key:
#                         resume_data['Education'][idx]['Dates'] = request.POST[key]
#                 except (ValueError, IndexError) as e:
#                     logger.warning(f"Invalid Education key format: {key}, error: {str(e)}")
#                     continue

#         # Process Projects
#         for key in request.POST:
#             if key.startswith('Projects['):
#                 try:
#                     idx = int(key.split('[')[1].split(']')[0])
#                     while len(resume_data['Projects']) <= idx:
#                         resume_data['Projects'].append({})
#                     if 'Name' in key:
#                         resume_data['Projects'][idx]['Name'] = request.POST[key]
#                     elif 'Description' in key:
#                         resume_data['Projects'][idx]['Description'] = request.POST[key]
#                 except (ValueError, IndexError) as e:
#                     logger.warning(f"Invalid Projects key format: {key}, error: {str(e)}")
#                     continue

#         # Convert Skills string to list
#         if isinstance(resume_data['Skills'], str):
#             try:
#                 # Handle JSON-like string from processed_resumes
#                 if resume_data['Skills'].startswith('['):
#                     resume_data['Skills'] = json.loads(resume_data['Skills'])
#                 else:
#                     resume_data['Skills'] = [s.strip() for s in resume_data['Skills'].split(',') if s.strip()]
#             except json.JSONDecodeError as e:
#                 logger.warning(f"Failed to parse Skills as JSON: {resume_data['Skills']}, error: {str(e)}")
#                 resume_data['Skills'] = [s.strip() for s in resume_data['Skills'].strip('[]').split(',') if s.strip()]
#         if not isinstance(resume_data['Skills'], list):
#             resume_data['Skills'] = []

#         # Parse Additional_Information if it's a JSON string
#         if isinstance(resume_data['Additional_Information'], str) and resume_data['Additional_Information'].startswith('{'):
#             try:
#                 resume_data['Additional_Information'] = json.loads(resume_data['Additional_Information'])
#             except json.JSONDecodeError as e:
#                 logger.warning(f"Failed to parse Additional_Information as JSON: {resume_data['Additional_Information']}, error: {str(e)}")

#         # Merge with existing OCR-parsed data
#         merged_resume_data = existing_resume_data.copy()
#         for section, value in resume_data.items():
#             if isinstance(value, list) and section in merged_resume_data:
#                 # Append non-empty new entries to existing lists
#                 merged_resume_data[section] = merged_resume_data[section] + [item for item in value if item]
#             elif value:  # Only update if non-empty
#                 merged_resume_data[section] = value

#         # Ensure all template sections are present
#         template_sections = [
#             'Personal_Information', 'Professional_Summary', 'Experience', 'Education',
#             'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information'
#         ]
#         for section in template_sections:
#             if section not in merged_resume_data:
#                 merged_resume_data[section] = [] if section in ['Experience', 'Education', 'Projects', 'Certifications_and_Licenses', 'References'] else ''

#         if request.method == 'POST':
#             # Save to processed_resumes
#             settings.MONGO_DB['processed_resumes'].update_one(
#                 {'original_pdf_id': pdf_id, 'user_id': user_id},
#                 {
#                     '$set': {
#                         'resume_data': merged_resume_data,
#                         'processed_at': datetime.now(),
#                         'user_id': user_id,
#                         'original_pdf_id': pdf_id
#                     }
#                 },
#                 upsert=True
#             )
#             logger.info(f"Resume saved for user {user_id}, pdf_id {pdf_id}")

#             # Handle application
#             temp_application = settings.MONGO_DB['temp_applications'].find_one({
#                 'user_id': user_id,
#                 'resume_id': pdf_id
#             })

#             if temp_application and temp_application.get('job_id'):
#                 settings.MONGO_DB['applications'].insert_one({
#                     'user_id': user_id,
#                     'job_id': temp_application['job_id'],
#                     'resume_id': temp_application['resume_id'],
#                     'applied_at': temp_application.get('applied_at', datetime.now()),
#                     'status': 'submitted',
#                     'application_data': {
#                         'submission_method': 'manual_edit',
#                         'submitted_at': datetime.now()
#                     }
#                 })

#                 # Trigger evaluation task
#                 evaluate_resume_task.delay(pdf_id, temp_application['job_id'])
#                 logger.info(f"Triggered evaluation for resume_id {pdf_id}, job_id {temp_application['job_id']}")
#             else:
#                 logger.warning(f"No valid temp_application found for resume_id {pdf_id}")

#             # Clean up temp_applications
#             settings.MONGO_DB['temp_applications'].delete_one({'resume_id': pdf_id})

#         return HttpResponseRedirect('/candidate/profile/')
#     except Exception as e:
#         logger.error(f"Error in submit_resume: {str(e)}", exc_info=True)
#         return render(request, 'candidate/error.html', {'message': str(e)})


# # @require_POST
# # @mongo_login_required
# # def submit_resume(request):
# #     try:
# #         user_id = str(request.mongo_user['user_id'])
# #         pdf_id = request.POST.get('pdf_id', '')

# #         processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
# #         existing_resume_data = processed_data.get('resume_data', {}) if processed_data else {}

# #         resume_data = {
# #             'Personal_Information': {
# #                 'Name': request.POST.get('Personal_Information[Name]', ''),
# #                 'Role': request.POST.get('Personal_Information[Role]', ''),
# #                 'Email': request.POST.get('Personal_Information[Email]', ''),
# #                 'Phone_number': request.POST.get('Personal_Information[Phone_number]', ''),
# #                 'LinkedIn': request.POST.get('Personal_Information[LinkedIn]', '')
# #             },
# #             'Professional_Summary': request.POST.get('Professional_Summary', ''),
# #             # 'Skills': request.POST.get('Skills', ''),
# #             'Skills':[],
# #             'Experience': [],
# #             'Education': [],
# #             'Projects': [],
# #             # 'Additional_Information': request.POST.get('Additional_Information', '')
# #             'Additional_Information': []
# #         }


# #         skills_raw = request.POST.get('Skills', '')
# #         try:
# #             resume_data['Skills'] = ast.literal_eval(skills_raw) if skills_raw else []
# #         except (ValueError, SyntaxError):
# #             resume_data['Skills'] = [skills_raw] if skills_raw else []

# #         additional_info_raw = request.POST.get('Additional_Information', '')
# #         try:
# #             resume_data['Additional_Information'] = ast.literal_eval(additional_info_raw) if additional_info_raw else {}
# #         except (ValueError, SyntaxError):
# #             resume_data['Additional_Information'] = {'info': additional_info_raw} if additional_info_raw else {}



# #         linkedin = resume_data['Personal_Information']['LinkedIn']
# #         if linkedin and not re.match(r'^(https?:\/\/)?([\w\d-]+\.)+[\w\d-]+(\/.*)?$', linkedin):
# #             logger.warning(f"Invalid LinkedIn URL: {linkedin}")
# #             return render(request, 'candidate/resume_form.html', {'resume': resume_data, 'error': 'Invalid LinkedIn URL'})

# #         for key in request.POST:
# #             if key.startswith('Experience['):
# #                 idx = int(key.split('[')[1].split(']')[0])
# #                 while len(resume_data['Experience']) <= idx:
# #                     resume_data['Experience'].append({})
# #                 if 'Job_Title' in key:
# #                     resume_data['Experience'][idx]['Job_Title'] = request.POST[key]
# #                 elif 'Company_Name' in key:
# #                     resume_data['Experience'][idx]['Company_Name'] = request.POST[key]
# #                 elif 'Dates_Duration' in key:
# #                     resume_data['Experience'][idx]['Dates_Duration'] = request.POST[key]
# #                 elif 'Job_Description' in key:
# #                     resume_data['Experience'][idx]['Job_Description'] = request.POST[key]

# #         for key in request.POST:
# #             if key.startswith('Education['):
# #                 idx = int(key.split('[')[1].split(']')[0])
# #                 while len(resume_data['Education']) <= idx:
# #                     resume_data['Education'].append({})
# #                 if 'Degree' in key:
# #                     resume_data['Education'][idx]['Degree'] = request.POST[key]
# #                 elif 'Institution' in key:
# #                     resume_data['Education'][idx]['Institution'] = request.POST[key]
# #                 elif 'Dates' in key:
# #                     resume_data['Education'][idx]['Dates'] = request.POST[key]

# #         for key in request.POST:
# #             if key.startswith('Projects['):
# #                 idx = int(key.split('[')[1].split(']')[0])
# #                 while len(resume_data['Projects']) <= idx:
# #                     resume_data['Projects'].append({})
# #                 if 'Name' in key:
# #                     resume_data['Projects'][idx]['Name'] = request.POST[key]
# #                 elif 'Description' in key:
# #                     resume_data['Projects'][idx]['Description'] = request.POST[key]

# #         merged_resume_data = existing_resume_data.copy()
# #         merged_resume_data.update(resume_data)
# #         template_sections = ['Personal_Information', 'Professional_Summary', 'Experience', 'Education', 
# #                             'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information']
# #         for section in template_sections:
# #             if section not in merged_resume_data:
# #                 merged_resume_data[section] = [] if section in ['Experience', 'Education', 'Projects', 'Certifications_and_Licenses', 'References'] else ''

# #         temp_application = settings.MONGO_DB['temp_applications'].find_one({
# #             'user_id': user_id,
# #             'resume_id': pdf_id
# #         })
        
# #         if temp_application:
# #             settings.MONGO_DB['applications'].insert_one({
# #                 'user_id': user_id,
# #                 'job_id': temp_application['job_id'],
# #                 'resume_id': temp_application['resume_id'],
# #                 'applied_at': temp_application.get('applied_at', datetime.now()),
# #                 'status': 'submitted',
# #                 'application_data': {
# #                     'submission_method': 'manual_edit',
# #                     'submitted_at': datetime.now()
# #                 }
# #             })

# #         settings.MONGO_DB['processed_resumes'].update_one(
# #             {'original_pdf_id': pdf_id, 'user_id': user_id},
# #             {
# #                 '$set': {
# #                     'resume_data': merged_resume_data,
# #                     'processed_at': datetime.now(),
# #                     'user_id': user_id,
# #                     'original_pdf_id': pdf_id
# #                 }
# #             },
# #             upsert=True
# #         )
# #         print(f"Final Resume saved for user {user_id}, pdf_id {pdf_id}")

# #         # Trigger evaluation task if application exists
# #         if temp_application:
# #             evaluate_resume_task.delay(pdf_id, temp_application['job_id'])
# #             print(f"Triggered evaluation task for resume {pdf_id}, job {temp_application['job_id']}")

# #         return HttpResponseRedirect('/candidate/profile/')
# #     except Exception as e:
# #         logger.error(f"Error in submit_resume: {str(e)}")
# #         return render(request, 'candidate/error.html', {'message': str(e)})































# # original code
from datetime import datetime
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
from bson.objectid import ObjectId  # For converting MongoDB ObjectId to string
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
            # settings.MONGO_DB['applications'].insert_one({
            settings.MONGO_DB['temp_applications'].insert_one({
                'user_id': user_id,
                'job_id': job_id,
                'resume_id': resume_id,
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




# original code 
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
        # processed_data = settings.MONGO_DB['processed_resumes'].find_one({'original_pdf_id': pdf_id})
        processed_data = settings.MONGO_DB['temp_processed_resumes'].find_one({'original_pdf_id': pdf_id})
        existing_resume_data = processed_data.get('resume_data', {}) if processed_data else {}

        # Extract form data
        resume_data = {
            'Personal_Information': {
                'Name': request.POST.get('Personal_Information[Name]', ''),
                'Role': request.POST.get('Personal_Information[Role]', ''),
                'Email': request.POST.get('Personal_Information[Email]', ''),
                'Phone_number': request.POST.get('Personal_Information[Phone_number]', ''),
                'LinkedIn': request.POST.get('Personal_Information[LinkedIn]', '')
            },
            'Professional_Summary': request.POST.get('Professional_Summary', ''),
            'Skills': request.POST.get('Skills', ''),
            'Experience': [],
            'Education': [],
            'Projects': [],
            'Additional_Information': request.POST.get('Additional_Information', '')
        }


        # Validate LinkedIn URL
        linkedin = resume_data['Personal_Information']['LinkedIn']
        if linkedin and not re.match(r'^(https?:\/\/)?([\w\d-]+\.)+[\w\d-]+(\/.*)?$', linkedin):
            logger.warning(f"Invalid LinkedIn URL: {linkedin}")
            return render(request, 'candidate/resume_form.html', {'resume': resume_data, 'error': 'Invalid LinkedIn URL'})

        # Process Experience
        for key in request.POST:
            if key.startswith('Experience['):
                idx = int(key.split('[')[1].split(']')[0])
                while len(resume_data['Experience']) <= idx:
                    resume_data['Experience'].append({})
                if 'Job_Title' in key:
                    resume_data['Experience'][idx]['Job_Title'] = request.POST[key]
                elif 'Company_Name' in key:
                    resume_data['Experience'][idx]['Company_Name'] = request.POST[key]
                elif 'Dates_Duration' in key:
                    resume_data['Experience'][idx]['Dates_Duration'] = request.POST[key]
                elif 'Job_Description' in key:
                    resume_data['Experience'][idx]['Job_Description'] = request.POST[key]

        # Process Education
        for key in request.POST:
            if key.startswith('Education['):
                idx = int(key.split('[')[1].split(']')[0])
                while len(resume_data['Education']) <= idx:
                    resume_data['Education'].append({})
                if 'Degree' in key:
                    resume_data['Education'][idx]['Degree'] = request.POST[key]
                elif 'Institution' in key:
                    resume_data['Education'][idx]['Institution'] = request.POST[key]
                elif 'Dates' in key:
                    resume_data['Education'][idx]['Dates'] = request.POST[key]

        # Process Projects
        for key in request.POST:
            if key.startswith('Projects['):
                idx = int(key.split('[')[1].split(']')[0])
                while len(resume_data['Projects']) <= idx:
                    resume_data['Projects'].append({})
                if 'Name' in key:
                    resume_data['Projects'][idx]['Name'] = request.POST[key]
                elif 'Description' in key:
                    resume_data['Projects'][idx]['Description'] = request.POST[key]

        # Merge with existing OCR-parsed data
        merged_resume_data = existing_resume_data.copy()
        merged_resume_data.update(resume_data)  # Update with form data
        # Ensure all fields from template are included
        template_sections = ['Personal_Information', 'Professional_Summary', 'Experience', 'Education', 
                            'Skills', 'Certifications_and_Licenses', 'Projects', 'References', 'Additional_Information']
        for section in template_sections:
            if section not in merged_resume_data:
                merged_resume_data[section] = [] if section in ['Experience', 'Education', 'Projects', 'Certifications_and_Licenses', 'References'] else ''
        # if request.method == 'POST':
        # Save merged data to MongoDB with timestamp
        # settings.MONGO_DB['processed_resumes'].update_one(
        # # settings.MONGO_DB['temp_processed_resumes'].update_one(
        #     {'original_pdf_id': pdf_id, 'user_id': user_id},
        #     {
        #         '$set': {
        #             'resume_data': merged_resume_data,
        #             'processed_at': datetime.now(),
        #             'user_id': user_id,
        #             'original_pdf_id': pdf_id
        #         }
        #     },
        #     upsert=True
        # )
        # print(f"temp_processed_resumes Resume saved for user {user_id}, pdf_id {pdf_id}")


    # if request.method == 'POST':
    # # Get the PDF ID from the form
    # pdf_id = request.POST.get('pdf_id', '')
    
    # # Find the corresponding temp application using user_id and pdf_id
    # temp_application = settings.MONGO_DB['temp_applications'].find_one({
    #     'user_id': user_id,
    #     'resume_id': pdf_id  # Assuming pdf_id is the same as resume_id
    # })
    
    # if temp_application:
    #     # Create permanent application record
    #     settings.MONGO_DB['applications'].insert_one({
    #         'user_id': user_id,
    #         'job_id': temp_application['job_id'],  # Get from temp record
    #         'resume_id': temp_application['resume_id'],  # Get from temp record
    #         'applied_at': temp_application.get('applied_at', datetime.now()),
    #         'status': 'submitted',
    #         'application_data': {
    #             'submission_method': 'manual_edit',
    #             'submitted_at': datetime.now()
    #         }
    #     })
        
        # Update processed resume (existing code)
        # settings.MONGO_DB['processed_resumes'].update_one(
        #     {'original_pdf_id': pdf_id, 'user_id': user_id},
        #     {
        #         '$set': {
        #             'resume_data': merged_resume_data,
        #             'processed_at': datetime.now(),
        #             'user_id': user_id,
        #             'original_pdf_id': pdf_id,
        #             'is_final': True
        #         }
        #     },
        #     upsert=True
        # )
        
        # Optional: Remove from temp collection
        # settings.MONGO_DB['temp_applications'].delete_one({'_id': temp_application['_id']})
        
        # print(f"Application finalized for user {user_id}, job {temp_application['job_id']}")


        print("0 request.method == 'POST': ",request.method == 'POST')
        if request.method == 'POST':
            print("1 request.method == 'POST': ",request.method == 'POST')

            pdf_id = request.POST.get('pdf_id', '')
    
            # Find the corresponding temp application using user_id and pdf_id
            temp_application = settings.MONGO_DB['temp_applications'].find_one({
                'user_id': user_id,
                'resume_id': pdf_id  # Assuming pdf_id is the same as resume_id
            })
            job_id = temp_application['job_id'] if temp_application else None

            
            if temp_application:
                # Create permanent application record
                settings.MONGO_DB['applications'].insert_one({
                    'user_id': user_id,
                    # 'job_id': temp_application['job_id'],  # Get from temp record
                    'job_id': job_id,  # Get from temp record
                    'resume_id': temp_application['resume_id'],  # Get from temp record
                    'applied_at': temp_application.get('applied_at', datetime.now()),
                    'status': 'submitted',
                    'application_data': {
                        'submission_method': 'manual_edit',
                        'submitted_at': datetime.now()
                    }
                })
 
            settings.MONGO_DB['processed_resumes'].update_one(
                {'original_pdf_id': pdf_id, 'user_id': user_id},
                {
                    '$set': {
                        'resume_data': merged_resume_data,
                        'processed_at': datetime.now(),
                        'user_id': user_id,
                        'original_pdf_id': pdf_id
                    }
                },
                upsert=True
                )
            print(f"Final Resume saved for user {user_id}, pdf_id {pdf_id}")

            # Retrieve the document to get its _id
            updated_document = settings.MONGO_DB['processed_resumes'].find_one(
            {'original_pdf_id': pdf_id, 'user_id': user_id}
            )

            if updated_document:
                resume_id = updated_document['_id']
                print(f"Document ID: {resume_id}")
            else:
                print("Document not found.")


            jobs_collection = settings.MONGO_DB["jobs"]
            resume_collection = settings.MONGO_DB["processed_resumes"]

            job = jobs_collection.find_one({"_id": ObjectId(job_id)})  # Use ObjectId for _id
            resume = resume_collection.find_one({"_id": ObjectId(resume_id)})  # Use ObjectId for _id

            # Print the document
            if job:
                # print(job)
                job_data = {
                    "_id": {"$oid": str(job["_id"])},
                    "job_details": job.get("job_details", {}),
                    "requirements": job.get("requirements", {}),
                    "experience": job.get("experience", []),
                    "education": job.get("education", []),
                    "weights": job.get("weights", {})
                }
                print(job_data)
                print(job_data["job_details"])
            else:
                print(f"No job found with _id: {job_id}")


            # Extract and format the resume_data
            if resume:
                resume_data = resume.get("resume_data", {})  # Extract the 'resume_data' key
                if resume_data:
                    print("\nResume Data found:")
                    print(resume_data)
                else:
                    print("No 'resume_data' found in the document.")
            else:
                print(f"No resume found with _id: {resume_id}")

            test_evaluations(resume_data, job_data)


               # Optional: Remove from temp collection
            # settings.MONGO_DB['temp_applications'].delete_one({'_id': temp_application['_id']})

        # Redirect to profile
        return HttpResponseRedirect('/candidate/profile/')
    except Exception as e:
        logger.error(f"Error in submit_resume: {str(e)}")
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
 
  

