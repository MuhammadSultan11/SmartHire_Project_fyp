import os
from django import forms
from django.conf import settings
from .models import PDFUpload
from django.core.files.storage import FileSystemStorage


class PDFUploadForm(forms.ModelForm):
    pdf_file = forms.FileField(label='Upload Resume (PDF)')
    def save(self):
        pdf_file = self.cleaned_data['pdf_file']
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'resumes'))
        filename = fs.save(pdf_file.name, pdf_file)
        return os.path.join(settings.MEDIA_ROOT, 'resumes', filename)
    
    class Meta:
        model = PDFUpload
        fields = ['pdf_file']


from django import forms
from bson import ObjectId

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    role = forms.CharField(max_length=20, required=False)

    def save(self, collection):
        import bcrypt
        password = self.cleaned_data['password'].encode('utf-8')
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        user_data = {
            'username': self.cleaned_data['username'],
            'email': self.cleaned_data['email'],
            'password': hashed,
            'role': self.cleaned_data.get('role', 'user')
        }
        return collection.insert_one(user_data)

class LoginForm(forms.Form):
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

class ProfileForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    title = forms.CharField(max_length=200, required=False)
    location = forms.CharField(max_length=100, required=False)
    about = forms.CharField(widget=forms.Textarea, required=False)
    social_links = forms.CharField(required=False)  # Will be JSON parsed in view

class ExperienceForm(forms.Form):
    title = forms.CharField(max_length=100, required=True)
    company = forms.CharField(max_length=100, required=True)
    location = forms.CharField(max_length=100, required=False)
    start_date = forms.CharField(max_length=7, required=True)  # YYYY-MM
    end_date = forms.CharField(max_length=7, required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)

class EducationForm(forms.Form):
    school = forms.CharField(max_length=100, required=True)
    degree = forms.CharField(max_length=100, required=True)
    start_date = forms.CharField(max_length=7, required=True)
    end_date = forms.CharField(max_length=7, required=False)
    grade = forms.CharField(max_length=20, required=False)

class CertificationForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    issuer = forms.CharField(max_length=100, required=True)
    issue_date = forms.CharField(max_length=7, required=True)
    expiration_date = forms.CharField(max_length=7, required=False)
    id = forms.CharField(max_length=50, required=False)

class ProjectForm(forms.Form):
    title = forms.CharField(max_length=100, required=True)
    start_date = forms.CharField(max_length=7, required=True)
    end_date = forms.CharField(max_length=7, required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    url = forms.URLField(required=False)

class SkillForm(forms.Form):
    name = forms.CharField(max_length=50, required=True)