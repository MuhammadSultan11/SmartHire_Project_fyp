from django.shortcuts import render

# Create your views here.

# Dashboard view
def dashboard(request):
    return render(request, 'dashboard.html')

# Homepage view
def job_post(request):
    return render(request, 'job_form.html')
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['hr_db']

@login_required
def hr_dashboard(request):
    jobs_col = db['jobs']
    candidates_col = db['candidates']
    reports_col = db['reports']
    notifications_col = db['notifications']

    # Fetch data
    jobs = list(jobs_col.find({'hr_id': str(request.user.id)}))  # Assuming HR linked to user ID
    job_filter = request.GET.get('job_id', '')
    if job_filter:
        jobs = [job for job in jobs if str(job['_id']) == job_filter]

    total_applications = candidates_col.count_documents({'job_id': {'$in': [str(job['_id']) for job in jobs]}})
    active_jobs = len([job for job in jobs if job.get('status') == 'active'])
    candidates = list(candidates_col.find({'job_id': {'$in': [str(job['_id']) for job in jobs]}, 'status': 'Shortlisted'}))
    # interviewed_reports = list(reports_col.find({'candidate_id': {'$in': [str(c['_id']) for c in candidates_col.find({'job_id': {'$in': [str(job['_id']) for job in jobs]})}]}}))
    candidate_ids = [str(c['_id']) for c in candidates_col.find({'job_id': {'$in': [str(job['_id']) for job in jobs]}})]
    interviewed_reports = list(reports_col.find({'candidate_id': {'$in': candidate_ids}}))
    notifications = list(notifications_col.find({'user_id': str(request.user.id)}).sort('timestamp', -1).limit(5))

    # Add computed fields
    for job in jobs:
        job['applications_count'] = candidates_col.count_documents({'job_id': str(job['_id'])})
        job['shortlisted_count'] = candidates_col.count_documents({'job_id': str(job['_id']), 'status': 'Shortlisted'})
        job['interviewed_count'] = candidates_col.count_documents({'job_id': str(job['_id']), 'status': 'Interviewed'})
    for candidate in candidates:
        candidate['job_title'] = next((j['title'] for j in jobs if str(j['_id']) == candidate['job_id']), 'Unknown')
    for report in interviewed_reports:
        candidate = candidates_col.find_one({'_id': ObjectId(report['candidate_id'])})
        report['candidate_name'] = candidate['name'] if candidate else 'Unknown'
        report['job_title'] = next((j['title'] for j in jobs if str(j['_id']) == candidate['job_id']), 'Unknown')

    # Analytics data (simplified)
    applications_data = [10, 20, 15, 25, 30]  # Replace with real data
    pipeline_data = {
        'Applied': candidates_col.count_documents({'job_id': {'$in': [str(job['_id']) for job in jobs]}}),
        'Shortlisted': candidates_col.count_documents({'job_id': {'$in': [str(job['_id']) for job in jobs]}, 'status': 'Shortlisted'}),
        'Interview Invited': candidates_col.count_documents({'job_id': {'$in': [str(job['_id']) for job in jobs]}, 'status': 'Interview Invited'}),
        'Interviewed': candidates_col.count_documents({'job_id': {'$in': [str(job['_id']) for job in jobs]}, 'status': 'Interviewed'}),
        'Hired': candidates_col.count_documents({'job_id': {'$in': [str(job['_id']) for job in jobs]}, 'status': 'Hired'})
    }

    context = {
        'jobs': jobs,
        'total_applications': total_applications,
        'active_jobs': active_jobs,
        'trend': '+10',  # Calculate dynamically if needed
        'candidates': candidates,
        'interviewed_reports': interviewed_reports,
        'notifications': notifications,
        'applications_data': applications_data,
        'pipeline_data': pipeline_data,
    }
    return render(request, 'hr_dashboard.html', context)

@login_required
def send_interview_invite(request, candidate_id):
    if request.method == 'POST':
        duration = request.POST.get('duration')
        candidates_col = db['candidates']
        candidate = candidates_col.find_one({'_id': ObjectId(candidate_id)})
        if candidate:
            # Generate interview link and set expiration
            invite_link = f"http://example.com/interview/{candidate_id}"  # Replace with real logic
            expiration = datetime.datetime.now() + datetime.timedelta(
                hours=24 if duration == '24h' else 48 if duration == '48h' else 72
            )
            candidates_col.update_one(
                {'_id': ObjectId(candidate_id)},
                {'$set': {'status': 'Interview Invited', 'invite_link': invite_link, 'invite_expires': expiration}}
            )
            # Send email (simplified)
            print(f"Sent invite to {candidate['name']} for {duration}: {invite_link}")
    return hr_dashboard(request)  # Re-render dashboard

# Placeholder views
def job_listing(request):
    return render(request, 'job_listing.html')  # Create this template if needed

def candidates_per_job(request, job_id):
    return render(request, 'candidates_per_job.html')  # Create this template

def view_report(request, report_id):
    return render(request, 'view_report.html')  # Create this template

def profile(request):
    return render(request, 'profile.html')  # Create this template

def logout(request):
    return redirect('login')  # Assuming you have a login view