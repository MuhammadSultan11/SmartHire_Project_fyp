from django.urls import path
from .views import upload_pdf, apply_job, get_resumes

urlpatterns = [
    # path('', landingpage, name='landingpage'),
    # path('', select_role, name='select_role'),
    # path('register/<str:role>/', register, name='register'),
    # path('login/', user_login, name='login'),
    # path('logout/', user_logout, name='logout'),
    # path('dashboard/', dashboard, name='dashboard'),
    path('apply/', apply_job, name='apply_job'),
    path('resumes/', get_resumes, name='get_resumes'),
    path('upload/', upload_pdf, name='upload_pdf'),  # Optional, if used

]
