from django import forms
import bcrypt

ROLE_CHOICES = (
    ('hr', 'HR'),
    ('candidate', 'Candidate'),
)

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150)
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, users_collection):
        hashed_password = bcrypt.hashpw(self.cleaned_data['password'].encode('utf-8'), bcrypt.gensalt())
        user_data = {
            "username": self.cleaned_data['username'],
            "full_name": self.cleaned_data['full_name'],
            "email": self.cleaned_data['email'],
            "password": hashed_password,
            "role": self.cleaned_data['role']
        }
        users_collection.insert_one(user_data)

class LoginForm(forms.Form):
    # username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
