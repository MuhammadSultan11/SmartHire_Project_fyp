from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib import messages
import bcrypt
from .forms import RegisterForm, LoginForm
from django.conf import settings

# MongoDB Collection
USERS_COLLECTION = settings.USERS_COLLECTION
SESSIONS_COLLECTION = settings.MONGO_DB['sessions']  # New session collection in MongoDB

def select_role(request):
    # return render(request, 'users/select_role.html')
    return render(request, 'select_role.html')

def register(request, role):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Check if user exists
            existing_user = USERS_COLLECTION.find_one({"username": form.cleaned_data['username']})
            if existing_user:
                messages.error(request, "Username already taken.")
            else:
                form.cleaned_data['role'] = role  # Automatically set role
                form.save(USERS_COLLECTION)
                messages.success(request, "Registration successful! Please log in.")
                return redirect('login')
    else:
        form = RegisterForm(initial={'role': role})
    # return render(request, 'users/register.html', {'form': form, 'role': role})
    return render(request, 'auth_pages/register.html', {'form': form, 'role': role})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        # print(form)
        if form.is_valid():
 
            print(form.cleaned_data)
            # user = USERS_COLLECTION.find_one({"username": form.cleaned_data['username']})
            user = USERS_COLLECTION.find_one({"email": form.cleaned_data['email']})
            print(user)
            if user and bcrypt.checkpw(form.cleaned_data['password'].encode('utf-8'), user['password']):
                print(user['email'])
                print(user['_id'])
                session_data = {
                    "user_id": str(user['_id']),
                    "email": user['email'],
                    "role": user['role']
                }
                session_id = SESSIONS_COLLECTION.insert_one(session_data).inserted_id  # Store session in MongoDB
                request.session['mongo_session_id'] = str(session_id)  # Store session ID in Django's session
                if session_data.get('role') == 'hr':
                    return redirect('dashboard')
                
                return redirect('index')
            else:
                messages.error(request, "Invalid credentials")
    else:
        form = LoginForm()
    return render(request, 'auth_pages/login1.html', {'form': form})


def user_logout(request):
    if 'mongo_session_id' in request.session:
        SESSIONS_COLLECTION.delete_one({"_id": request.session['mongo_session_id']})  # Remove session from MongoDB
    request.session.flush()  # Clear Django session
    return redirect('login')

# def dashboard(request):
#     if 'user_id' not in request.session:
#         return redirect('login')
#     return render(request, 'dashboard.html', {'username': request.session.get('username'), 'role': request.session.get('role')})
from bson import ObjectId  # Import ObjectId

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

def index(request):
    return render(request, 'index.html')

def landingpage(request):
    return render(request, 'landingpage.html')