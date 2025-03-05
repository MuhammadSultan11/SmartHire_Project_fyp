from django.urls import path
from .views import upload_pdf

urlpatterns = [
    # path('', landingpage, name='landingpage'),
    # path('', select_role, name='select_role'),
    # path('register/<str:role>/', register, name='register'),
    # path('login/', user_login, name='login'),
    # path('logout/', user_logout, name='logout'),
    # path('dashboard/', dashboard, name='dashboard'),
    path('upload/', upload_pdf, name='upload_pdf'),
    

]
