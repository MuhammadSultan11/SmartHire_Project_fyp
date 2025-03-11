from datetime import datetime
import json
from django.shortcuts import redirect, render
from django.conf import settings
from .forms import PDFUploadForm
from accounts.views import mongo_login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import os
import logging

logger = logging.getLogger(__name__)

USERS_COLLECTION = settings.USERS_COLLECTION
SESSIONS_COLLECTION = settings.MONGO_DB['sessions']

def upload_pdf(request):
    if request.method == 'POST':
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_pdf = form.save()
            return redirect('process_resume', pdf_id=uploaded_pdf.id)
    else:
        form = PDFUploadForm()
    return render(request, 'upload_pdf.html', {'form': form})

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
            
            application = {
                'user_id': str(request.mongo_user['user_id']),
                'job_id': job_id,
                'resume_id': str(resume_id),
                'applied_at': datetime.now()
            }
            settings.MONGO_DB['applications'].insert_one(application)
            logger.info(f"Application submitted: User {request.mongo_user['user_id']}, Job {job_id}")
            return JsonResponse({'success': True})
        
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