from datetime import datetime
import json
import uuid
from django.shortcuts import redirect, render
from django.conf import settings
from .forms import PDFUploadForm
from accounts.views import mongo_login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import os
import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from .forms import PDFUploadForm
from .models import PDFUpload
from .prompts import resume_prompt, resume_data_template
import re
import ast  # For safely evaluating strings to Python objects
from django.shortcuts import render, redirect
from .forms import PDFUploadForm
from .models import PDFUpload
from .ocr_utils import process_pdf_with_alignment_ocr, Experiments22, get_genai_response, extract_combined_text
# import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from bson import ObjectId

 
logger = logging.getLogger(__name__)

USERS_COLLECTION = settings.USERS_COLLECTION
SESSIONS_COLLECTION = settings.MONGO_DB['sessions']

 
def serialize_mongo_document(doc):
    if doc is None:
        return {}
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc




def upload_pdf(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_pdf = form.save()
            return redirect('process_resume', pdf_id=uploaded_pdf.id)
    else:
        form = PDFUploadForm()
    return render(request, 'upload_pdf.html', {'form': form})



def extract_section(cv_text, section_name):
    # Update the regex to adapt to the actual string formatting
    pattern = re.compile(rf"'{section_name}':\s*(\[[^]]*\]|{{[^}}]*}}|'.*?')", re.DOTALL)

    match = pattern.search(cv_text)
    result = ''
    if match:
        return match.group(1).strip()
    return f"Section '{section_name}' not found."


@mongo_login_required
def process_resume(request, pdf_id):
    response1 = ""
    response2 = ""
    response4 = ""
    try:
        # Convert pdf_id string to ObjectId for MongoDB query
        try:
            pdf_object_id = ObjectId(pdf_id)
        except Exception as e:
            logger.error(f"Invalid pdf_id format: {pdf_id} - {str(e)}")
            return render(request, 'candidate/error.html', {'message': "Invalid resume ID format."})

        # Fetch the resume from MongoDB
        uploaded_pdf = settings.MONGO_DB['resumes'].find_one({'_id': pdf_object_id})
        if not uploaded_pdf:
            logger.error(f"No resume found for pdf_id: {pdf_id}")
            return render(request, 'candidate/error.html', {'message': "The requested PDF does not exist."})

        pdf_path = uploaded_pdf['path']
        logger.info(f"Processing resume at path: {pdf_path}")
    # try:
    #     # Fetch the resume from MongoDB using the string pdf_id
    #     uploaded_pdf = settings.MONGO_DB['resumes'].find_one({'_id': pdf_id})
    #     if not uploaded_pdf:
    #         return render(request, 'candidate/error.html', {'message': "The requested PDF does not exist."})

    #     pdf_path = uploaded_pdf['path']

        # Run OCR processes in parallel
        with ThreadPoolExecutor() as executor:
            future1 = executor.submit(Experiments22, pdf_path)
            future2 = executor.submit(process_pdf_with_alignment_ocr, pdf_path)
            
            extracted_text1 = future1.result()
            extracted_text2 = future2.result()
        
        combined_text = extracted_text1 + "\n" + extracted_text2       
 
        response1 = resume_prompt.format(resume_text=combined_text)
        logger.debug(f"Response1: {response1}")
        print("\n\n response1 :",response1)


        response2 = get_genai_response(response1)
        print("\n\n response2 :",response2)
        logger.debug(f"Response2: {response2}")

        prompt = f"""
        Please recheck if any details are missing, then fill them. Convert the following input into the given Python 
        dictionary template format and return it as valid Python code. Ensure all fields in the template are included, 
        even if they are empty (use None, empty lists, or strings as appropriate).
        Input: {response2 + response1}
        Template Format:
        {resume_data_template}

        Output must strictly follow Template Format. Do not introduce any additional structures or variations.
        """
        response3 = get_genai_response(prompt)

        response4 = response3.strip()
        if response4.startswith("```json"):
            response4 = response4.removeprefix("```json\n").removesuffix("\n```")
        if response4.startswith("```python"):
            response4 = response4.removeprefix("```python\n").removesuffix("\n```")
            # response4 = response4.removeprefix(" resume_dict = ")

        resume_data = response4

        sections = [
            'Personal_Information', 
            'Professional_Summary', 
            'Experience',
            'Education', 
            'Skills', 
            'Certifications_and_Licenses', 
            'Projects', 
            'References', 
            'Additional_Information'    
        ]

        combined_dict = {}
        for section in sections:
            extracted_content = extract_section(response4, section)
            if extracted_content:
                try:
                    combined_dict[section] = ast.literal_eval(extracted_content)
                    # combined_dict[section] = json.loads(extracted_content)
                except (ValueError, SyntaxError) as e:
                    logger.warning(f"Could not parse {section} as Python dict: {e}")
                    combined_dict[section] = extracted_content  # Fallback to string

        if not isinstance(combined_dict, dict):
            logger.error("Parsed data is not a dictionary.")
            return render(request, 'candidate/error.html', {'message': "Failed to parse resume data into a dictionary."})

        # Merge Contextual_Career_Experience if present (though not in your template)
        if "Experience" in combined_dict and "Contextual_Career_Experience" in combined_dict:
            combined_dict["Experience"] += combined_dict.pop("Contextual_Career_Experience", [])
        print("\n\n combined_dict :",combined_dict)
        
        return render(request, 'candidate/resume_form.html', context={'resume': combined_dict})

    except Exception as e:
        logger.error(f"Error in process_resume: {str(e)}")
        response_message = str(response4) if 'response4' in locals() else "No response data"
        return render(request, 'candidate/error.html', {'message': response_message + " - " + str(e)})


def resume_form(request, resume_data=None):
    if resume_data is None:
        resume_data = {}  # Default empty dictionary if no data provided

    if "Experience" in resume_data and "Contextual_Career_Experience" in resume_data:
        resume_data["Experience"] += resume_data["Contextual_Career_Experience"]
        del resume_data["Contextual_Career_Experience"]
    
    return render(request, 'candidate/resume_form.html', context={'resume': resume_data})



# Existing imports remain

@mongo_login_required
@require_POST
def apply_job(request):
    try:
        if 'resume' in request.FILES:
            resume_file = request.FILES['resume']
            job_id = request.POST.get('job_id')
            if not resume_file.name.endswith('.pdf'):
                return JsonResponse({'success': False, 'error': 'Please upload a PDF file'}, status=400)
            
            file_path = os.path.join('resumes', str(request.mongo_user['user_id']), resume_file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb+') as destination:
                for chunk in resume_file.chunks():
                    destination.write(chunk)
            
            resume_doc = {
                'user_id': str(request.mongo_user['user_id']),
                'name': resume_file.name,
                'path': file_path,
                'uploaded_at': datetime.now()
            }
            resume_id = settings.MONGO_DB['resumes'].insert_one(resume_doc).inserted_id
            logger.info(f"Inserted resume with ID: {resume_id}")
            
            application = {
                'user_id': str(request.mongo_user['user_id']),
                'job_id': job_id,
                'resume_id': str(resume_id),
                'applied_at': datetime.now()
            }
            settings.MONGO_DB['applications'].insert_one(application)
            logger.info(f"Application submitted: User {request.mongo_user['user_id']}, Job {job_id}")

            # For real-time updates, you could store progress in MongoDB and poll/WebSocket it
            return JsonResponse({
                'success': True,
                'message': 'Application submitted successfully. Resume is being processed.',
                'resume_id': str(resume_id)
            })
        
        else:
            data = json.loads(request.body)
            job_id = data.get('job_id')
            resume_id = data.get('resume_id')
            if not job_id or not resume_id:
                return JsonResponse({'success': False, 'error': 'Missing job_id or resume_id'}, status=400)
            
            application = {
                'user_id': str(request.mongo_user['user_id']),
                'job_id': job_id,
                'resume_id': resume_id,
                'applied_at': datetime.now()
            }
            settings.MONGO_DB['applications'].insert_one(application)
            logger.info(f"Application submitted with existing resume: User {request.mongo_user['user_id']}, Job {job_id}")
            return JsonResponse({'success': True})
    
    except Exception as e:
        logger.error(f"Error in apply_job: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



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
        logger.info(f"Resumes fetched for user: {request.mongo_user['user_id']}")
        return JsonResponse({'success': True, 'resumes': resume_list})
    except Exception as e:
        logger.error(f"Error in get_resumes: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@mongo_login_required
@require_POST # receive data from form and save in data base
def submit_resume(request):
    try:
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
        
        # Optional: Validate LinkedIn URL
        linkedin = resume_data['Personal_Information']['LinkedIn']
        if linkedin and not re.match(r'^(https?:\/\/)?([\w\d-]+\.)+[\w\d-]+(\/.*)?$', linkedin):
            logger.warning(f"Invalid LinkedIn URL: {linkedin}")
            # Optionally redirect back with an error message
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

        # Save to MongoDB (example; adjust based on your needs)
        user_id = str(request.mongo_user['user_id'])
        settings.MONGO_DB['processed_resumes'].update_one(
            {'user_id': user_id, 'original_pdf_id': request.POST.get('pdf_id', '')},
            {'$set': resume_data},
            upsert=True
        )
        logger.info(f"Resume saved for user {user_id}")

        # Redirect to a success page or profile
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

