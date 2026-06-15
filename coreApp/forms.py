import re
from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import HospitalName

# ফোন নম্বরের জন্য ১১ ডিজিটের কাস্টম ভ্যালিডেটর (শুধুমাত্র ০১ দিয়ে শুরু হওয়া ১১টি সংখ্যা):
phone_validator = RegexValidator(
    regex=r'^01[3-9]\d{8}$',
    message="Phone number must be exactly 11 digits and start with a valid Bangladeshi operator prefix (e.g., 017xxxxxxxx)."
)

# ====================  পেশেন্ট রেজিস্ট্রেশন ফর্ম ====================
class PatientRegisterForm(forms.Form):
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'John Doe'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'yourname@example.com'})
    )
    nid_number = forms.CharField(
        max_length=17, 
        min_length=10, 
        required=True, 
        label="NID Number",
        widget=forms.TextInput(attrs={'placeholder': 'Enter 10, 13 or 17 digit NID'})
    )
    date_of_birth = forms.DateField(
        required=True, 
        label="Date of Birth",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'cursor-pointer'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a secure password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'})
    )

    # NID-এর ডিজিট ও ফরম্যাট চেক :
    def clean_nid_number(self):
        nid = self.cleaned_data.get('nid_number')
        if not re.match(r'^([0-9]{10}|[0-9]{13}|[0-9]{17})$', nid):
            raise ValidationError("অনুগ্রহ করে একটি বৈধ ১০, ১৩ অথবা ১৭ ডিজিটের NID নম্বর দিন।")
        return nid

    # ইমেইল ডুপ্লিকেট চেক :
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    # পাসওয়ার্ড এবং অন্যান্য গ্লোবাল ভ্যালিডেশন চেক :
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match!")
            
        if password and len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
            
        return cleaned_data


# ====================  হসপিটাল রেজিস্ট্রেশন ফর্ম ====================
class HospitalRegisterForm(forms.Form):
    hospital_name = forms.CharField(
        max_length=200, 
        widget=forms.TextInput(attrs={'placeholder': 'Official Hospital Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Official Hospital Email'})
    )
    contact_number = forms.CharField(
        validators=[phone_validator], 
        max_length=11, min_length=11,
        widget=forms.TextInput(attrs={'placeholder': 'Emergency Contact Number (11 digits)'})
    )
    location = forms.CharField(
        max_length=250, 
        widget=forms.TextInput(attrs={'placeholder': 'Full Address (e.g., Dhanmondi, Dhaka)'})
    )
    license_number = forms.CharField(
        max_length=50, 
        widget=forms.TextInput(attrs={'placeholder': 'DGHS License/Registration Number'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Create a secure password'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match!")
            
        return cleaned_data


# ==================== ইমেইল ভিত্তিক কাস্টম লগইন ফর্ম ====================
class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your registered email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'})
    )