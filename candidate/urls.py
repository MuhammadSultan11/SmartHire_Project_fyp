# # from django.urls import path
# # from .views import upload_pdf, apply_job, get_resumes, candidate_profile
# # from . import views

# # urlpatterns = [
# #     path('apply/', views.apply_job, name='apply_job'),
# #     path('resumes/', views.get_resumes, name='get_resumes'),
# #     path('upload/', views.upload_pdf, name='upload_pdf'),  # Optional, if used
# #     path('profile/', views.candidate_profile, name='candidate_profile'),
# #     path('api/profile/', views.api_profile, name='api_profile'),
# #     path('api/experience/', views.api_experience, name='api_experience'),
# #     path('api/education/', views.api_education, name='api_education'),
# #     path('api/certification/', views.api_certification, name='api_certification'),
# #     path('api/project/', views.api_project, name='api_project'),
# #     path('api/skill/', views.api_skill, name='api_skill'),

# # ]


# # candidate/urls.py
# from django.conf import settings
# from django.urls import path
# from .views import upload_pdf, apply_job, get_resumes, candidate_profile, api_profile, api_experience, api_education, api_certification, api_project, api_skill
# from . import views
# from django.conf.urls.static import static

# urlpatterns = [
#     path('apply/', apply_job, name='apply_job'),
#     path('resumes/', get_resumes, name='get_resumes'),
#     path('upload/', upload_pdf, name='upload_pdf'),
#     # path('profile/', candidate_profile, name='candidate_profile'),
#     # path('api/profile/', api_profile, name='api_profile'),
#     # path('api/experience/', api_experience, name='api_experience'),
#     # path('api/education/', api_education, name='api_education'),
#     # path('api/certification/', api_certification, name='api_certification'),
#     # path('api/project/', api_project, name='api_project'),
#     # path('api/skill/', api_skill, name='api_skill'),



#    path('apply/', apply_job, name='apply_job'),
#     path('resumes/', get_resumes, name='get_resumes'),
#     path('upload/', upload_pdf, name='upload_pdf'),
#     path('profile/', views.candidate_profile, name='candidate_profile'),
#     path('api/profile/', views.api_profile, name='api_profile'),
#     path('api/profile/picture/', views.api_profile_picture, name='api_profile_picture'),
#     path('api/experience/', views.api_experience, name='api_experience'),
#     path('api/experience/<str:item_id>/', views.api_experience, name='api_experience_detail'),
#     path('api/education/', views.api_education, name='api_education'),
#     path('api/education/<str:item_id>/', views.api_education, name='api_education_detail'),
#     path('api/certification/', views.api_certification, name='api_certification'),
#     path('api/certification/<str:item_id>/', views.api_certification, name='api_certification_detail'),
#     path('api/project/', views.api_project, name='api_project'),
#     path('api/project/<str:item_id>/', views.api_project, name='api_project_detail'),
#     path('api/skill/', views.api_skill, name='api_skill'),
#     path('api/skill/<str:item_id>/', views.api_skill, name='api_skill_detail'),

#     ]
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.urls import path
from .views import upload_pdf, apply_job,task_status, get_resumes, candidate_profile, api_profile,api_experience, api_education, api_certification, api_project, api_skill,api_profile_picture, process_resume, submit_resume
from django.conf import settings
from django.conf.urls.static import static
from . import consumers

urlpatterns = [
path('task_status/<str:task_id>/',  task_status, name='task_status'),
    path('ws/progress/<str:task_id>/', consumers.ProgressConsumer.as_asgi()),
    path('upload/', upload_pdf, name='upload_pdf'),
    # path('edit_resume/<str:resume_id>/', edit_resume, name='edit_resume'),
    path('process_resume/<str:pdf_id>/', process_resume, name='process_resume'),
    path('apply/', apply_job, name='apply_job'),
    path('resumes/', get_resumes, name='get_resumes'),
      
    path('upload/', upload_pdf, name='upload_pdf'),
    path('submit_resume/', submit_resume, name='submit_resume'),
    path('profile/', candidate_profile, name='candidate_profile'),
    path('api/profile/', api_profile, name='api_profile'),
    path('api/profile/picture/', api_profile_picture, name='api_profile_picture'),
    path('api/experience/', api_experience, name='api_experience'),
    path('api/experience/<str:item_id>/', api_experience, name='api_experience_detail'),
    path('api/education/', api_education, name='api_education'),
    path('api/education/<str:item_id>/', api_education, name='api_education_detail'),
    path('api/certification/', api_certification, name='api_certification'),
    path('api/certification/<str:item_id>/', api_certification, name='api_certification_detail'),
    path('api/project/', api_project, name='api_project'),
    path('api/project/<str:item_id>/', api_project, name='api_project_detail'),
    path('api/skill/', api_skill, name='api_skill'),
    path('api/skill/<str:item_id>/', api_skill, name='api_skill_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

