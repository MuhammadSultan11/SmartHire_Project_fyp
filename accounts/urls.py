from django.urls import path
from .accounts_views import register, user_login, user_logout, dashboard, landingpage, index, job_detail

urlpatterns = [
    
    # path('', select_role, name='select_role'),
    path('register/<str:role>/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('index/', index, name='index'),
     path('', landingpage, name='landingpage'),
    path('job/<str:job_id>/', job_detail, name='job_detail'),
   
]
