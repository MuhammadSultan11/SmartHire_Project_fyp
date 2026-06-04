from django.urls import path
# from .views import job_post, dashboard

from . import employers_views



urlpatterns = [
    # path('', landingpage, name='landingpage'),
    # path('', select_role, name='select_role'),
    # path('register/<str:role>/', register, name='register'),


    path('', employers_views.hr_dashboard, name='hr_dashboard'),
    # path('send_interview_invite/<str:candidate_id>/', views.send_interview_invite, name='send_interview_invite'),
    # path('job_listing/', employers_views.job_listing, name='job_listing'),
 
         
    path('job_posting/', employers_views.job_postform_view, name='job_posting'),
   

 
     
    path('login/', employers_views.login_signup, name='login_signup'),
    path('job_detail/<str:job_id>/', employers_views.job_detail, name='job_detail'),
    path('job_edit/<str:job_id>/', employers_views.job_edit, name='job_edit'),
    path('job_delete/<str:job_id>/', employers_views.job_delete, name='job_delete'),
    # path('candidate_listing/', employers_views.candidate_listing, name='candidate_listing'),
    # path('candidates_per_job/<str:job_id>/', employers_views.candidates_per_job, name='candidates_per_job'),
    path('interview_filtered_candidates/', employers_views.interview_filtered_candidates, name='interview_filtered_candidates'),
 
    path('job/edit/<str:job_id>/', employers_views.job_edit, name='edit_job'),
    path('job/close/<str:job_id>/', employers_views.close_job, name='close_job'),
]
