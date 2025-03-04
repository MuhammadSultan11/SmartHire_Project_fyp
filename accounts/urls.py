from django.urls import path
from .views import select_role, register, user_login, user_logout, dashboard, landingpage, index

urlpatterns = [
    path('', landingpage, name='landingpage'),
    # path('', select_role, name='select_role'),
    path('register/<str:role>/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('index/', index, name='index'),
    
]
