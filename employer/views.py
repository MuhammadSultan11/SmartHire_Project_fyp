from django.shortcuts import render

# Create your views here.

# Dashboard view
def dashboard(request):
    return render(request, 'dashboard.html')

# Homepage view
def job_post(request):
    return render(request, 'job_form.html')
