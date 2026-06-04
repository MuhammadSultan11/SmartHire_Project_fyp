# import datetime
from datetime import datetime, timedelta
import logging

from bson import ObjectId
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
import bcrypt
from .forms import RegisterForm, LoginForm
from django.conf import settings
from bson import ObjectId
from django.urls import reverse
 

# MongoDB Collection
USERS_COLLECTION = settings.USERS_COLLECTION
SESSIONS_COLLECTION = settings.MONGO_DB['sessions']  # New session collection in MongoDB
 

logger = logging.getLogger(__name__)


# Custom decorator for MongoDB session check
def mongo_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        session_id = request.session.get('mongo_session_id')
        if not session_id:
            return redirect('login')
        try:
            session = SESSIONS_COLLECTION.find_one({'_id': ObjectId(session_id)})
        except Exception as e:
            logger.error(f"Invalid session ID: {session_id}, Error: {str(e)}")
            return redirect('login')
        if not session:
            logger.info(f"Session expired or not found: {session_id}")
            return redirect('login')
        request.mongo_user = session
        return view_func(request, *args, **kwargs)
    return wrapper



def register(request, role):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Check if user exists
            existing_username = USERS_COLLECTION.find_one({"username": form.cleaned_data['username']})
            existing_email = USERS_COLLECTION.find_one({"email": form.cleaned_data['email']})
            if existing_username:
                messages.error(request, "Username already taken.")
            if existing_email:
                messages.error(request, "Email already taken.")
            else:
                form.cleaned_data['role'] = role  # Automatically set role
                form.save(USERS_COLLECTION)
                messages.success(request, "Registration successful! Please log in.")
                return redirect('login')
    else:
        form = RegisterForm(initial={'role': role})
    # return render(request, 'users/register.html', {'form': form, 'role': role})
    return render(request, 'auth_pages/register.html', {'form': form, 'role': role})


# candidate/views.py (from your code, verified)
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = USERS_COLLECTION.find_one({"email": form.cleaned_data['email']})
            if user and bcrypt.checkpw(form.cleaned_data['password'].encode('utf-8'), user['password']):
                session_data = {
                    "user_id": str(user['_id']),
                    "email": user['email'],
                    "role": user['role'],
                    "created_at": datetime.now()
                }
                
                existing_session = SESSIONS_COLLECTION.find_one({"user_id": str(user['_id'])})
                if existing_session:
                    SESSIONS_COLLECTION.update_one(
                        {"user_id": str(user['_id'])},
                        {"$set": session_data}
                    )
                    session_id = str(existing_session['_id'])
                else:
                    session_id = str(SESSIONS_COLLECTION.insert_one(session_data).inserted_id)
                
                request.session['mongo_session_id'] = session_id
                request.session['user_id'] = str(user['_id'])  # Added for consistency
                request.session.modified = True
                logger.info(f"User logged in: {user['email']}, Session ID: {session_id}, User ID: {str(user['_id'])}")
                
                if session_data.get('role') == 'hr':
                    return JsonResponse({'success': True, 'redirect': reverse('hr_dashboard')})
                return JsonResponse({'success': True, 'redirect': '/index/'})
            else:
                messages.error(request, "Invalid credentials")
                return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
    else:
        form = LoginForm()
    return render(request, 'auth_pages/login1.html', {'form': form})


def user_logout(request):
    session_id = request.session.get('mongo_session_id')
    if session_id:
        try:
            SESSIONS_COLLECTION.delete_one({"_id": ObjectId(session_id)})
            logger.info(f"Session deleted: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {str(e)}")
    request.session.flush()
    return redirect('login')



def dashboard(request):
    if 'mongo_session_id' not in request.session :
        return redirect('login')
    try:
        session_data = SESSIONS_COLLECTION.find_one({"_id": ObjectId(request.session['mongo_session_id'])})
    except:
        session_data = None

    # session_data = SESSIONS_COLLECTION.find_one({"_id": request.session['mongo_session_id']})
    if not session_data:
        return redirect('login') 

    if session_data.get('role') != 'hr':
        messages.error(request, "Access denied. HR role required.")
        return redirect('login')

    return render(request, 'employer/dashboard.html', {
        'email': session_data.get('email'),
        'role': session_data.get('role')
    })


def landingpage(request):
    return render(request, 'landingpage.html')

def index(request):
    jobs_collection = settings.MONGO_DB["jobs"]
    
    # Get filter parameters from GET request
    search = request.GET.get('search', '')
    job_type = request.GET.get('jobType', '')
    work_arrangement = request.GET.get('workArrangement', '')
    location = request.GET.get('location', '')
    experience = request.GET.get('experience', '')
    salary_min = request.GET.get('salaryMin', '')
    salary_max = request.GET.get('salaryMax', '')
    posted_date = request.GET.get('postedDate', '')

    # Build MongoDB query
    query = {}
    
    if search:
        query['$or'] = [
            {'job_details.position_title': {'$regex': search, '$options': 'i'}},
            {'job_details.job_description': {'$regex': search, '$options': 'i'}},
            {'company_details.name': {'$regex': search, '$options': 'i'}}
        ]
    
    if job_type:
        query['job_type.type'] = job_type
    
    if work_arrangement:
        query['job_type.work_arrangement'] = work_arrangement
    
    if location:
        query['compensation.location'] = {'$regex': location, '$options': 'i'}
    
    if experience:
        exp_range = experience.split('-')
        if len(exp_range) == 2:
            min_exp, max_exp = map(int, exp_range)
            query['experience'] = {
                '$elemMatch': {
                    'years': {'$gte': min_exp, '$lte': max_exp}
                }
            }
    
    if salary_min:
        query['compensation.min_salary'] = {'$gte': int(salary_min)}
    if salary_max:
        query['compensation.max_salary'] = {'$lte': int(salary_max)}
    
    if posted_date:
        days = int(posted_date)
        query['created_at'] = {
            '$gte': datetime.now() - timedelta(days=days)
        }

    # Fetch jobs with filters
    jobs = list(jobs_collection.find(query).sort("created_at", -1))
    
    # Convert ObjectId to string
    for job in jobs:
        job['id'] = str(job['_id'])
        del job['_id']

    context = {
        'jobs': jobs,
        'filters': {
            'search': search,
            'jobType': job_type,
            'workArrangement': work_arrangement,
            'location': location,
            'experience': experience,
            'salaryMin': salary_min,
            'salaryMax': salary_max,
            'postedDate': posted_date
        }
    }
    return render(request, 'index.html', context)



logger = logging.getLogger(__name__)

def job_detail(request, job_id):
    try:
        logger.info(f"Fetching job with ID: {job_id}")
        job = settings.MONGO_DB["jobs"].find_one({'_id': ObjectId(job_id)})
        if not job:
            logger.warning(f"Job not found for ID: {job_id}")
            return render(request, 'partials/_job_detail.html', {'error': 'Job not found'}, status=404)
        job['id'] = str(job['_id'])
        logger.info(f"Job found: {job['job_details']['position_title']}")
        return render(request, 'partials/_job_detail.html', {'job': job})
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {str(e)}")
        return render(request, 'partials/_job_detail.html', {'error': str(e)}, status=500)