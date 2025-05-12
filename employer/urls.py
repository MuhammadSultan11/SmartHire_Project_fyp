from django.urls import path
# from .views import job_post, dashboard

from . import employers_views

urlpatterns = [
    # path('', landingpage, name='landingpage'),
    # path('', select_role, name='select_role'),
    # path('register/<str:role>/', register, name='register'),
    # path('login/', user_login, name='login'),
    # path('logout/', user_logout, name='logout'),
    # path('dashboard/', dashboard, name='dashboard'),

    path('post_job/', employers_views.job_post, name='post_job'),
    path('dashboard/',employers_views.dashboard, name='dashboard'),


    path('', employers_views.hr_dashboard, name='hr_dashboard'),
    # path('send_interview_invite/<str:candidate_id>/', views.send_interview_invite, name='send_interview_invite'),
    path('job_listing/', employers_views.job_listing, name='job_listing'),
    path('candidates_per_job/<str:job_id>/', employers_views.candidates_per_job, name='candidates_per_job'),
    # path('view_report/<str:report_id>/', views.view_report, name='view_report'),
    path('profile/', employers_views.profile, name='profile'),
    # path('logout/', views.logout, name='logout'),
    

    # path('job_posting/', views.job_posting, name='job_posting'),
    path('job_posting/', employers_views.job_form_view, name='job_posting'),
        # path('post-job/', views.job_posting_form, name='job_posting_form'),



 
 
    path('', employers_views.hr_dashboard, name='hr_dashboard'),
    path('login/', employers_views.login_signup, name='login_signup'),
    path('job_listing/', employers_views.job_listing, name='job_listing'),
    path('job_detail/<str:job_id>/', employers_views.job_detail, name='job_detail'),
    path('job_edit/<str:job_id>/', employers_views.job_edit, name='job_edit'),
    path('job_delete/<str:job_id>/', employers_views.job_delete, name='job_delete'),
    path('candidate_listing/', employers_views.candidate_listing, name='candidate_listing'),
    path('candidates_per_job/<str:job_id>/', employers_views.candidates_per_job, name='candidates_per_job'),
    path('interview_filtered_candidates/', employers_views.interview_filtered_candidates, name='interview_filtered_candidates'),
    # path('hr_review/', views.hr_review, name='hr_review'),
    # path('resume_analysis/', views.resume_analysis, name='resume_analysis'),
    # path('candidate_comparison/', views.candidate_comparison, name='candidate_comparison'),
    # path('criteria_config/', views.criteria_config, name='criteria_config'),
    # path('video_call/', views.video_call, name='video_call'),
    # path('interview_scheduling/', views.interview_scheduling, name='interview_scheduling'),
    # path('job_analytics/', views.job_analytics, name='job_analytics'),
    # path('bulk_action/', views.bulk_action, name='bulk_action'),
    # path('report_viewing/<str:report_id>/', views.report_viewing, name='report_viewing'),
    # path('notification_settings/', views.notification_settings, name='notification_settings'),
    # path('hr_profile/', views.hr_profile, name='hr_profile'),
 

]
