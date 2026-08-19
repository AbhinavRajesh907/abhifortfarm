from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from .models import User, ProviderProfile


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class BaseRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'username', 'address', 'city', 'state', 'pincode']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
            'address': forms.TextInput(attrs={'placeholder': 'Address'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'placeholder': 'Pincode'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match")
        
        return cleaned_data

class UserRegistrationForm(BaseRegistrationForm):
    pass

class ProviderRegistrationForm(BaseRegistrationForm):
    # Provider specific fields
    farm_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Farm/Business Name'}))
    farm_address = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Farm Address'}))
    provider_type = forms.ChoiceField(choices=[
        ('Plant Nursery', 'Plant Nursery'),
        ('Seed Supplier', 'Seed Supplier'),
        ('Farmer', 'Farmer'),
        ('Agricultural Farm', 'Agricultural Farm'),
        ('Gardening Supplier', 'Gardening Supplier'),
        ('Other', 'Other')
    ])
    experience_years = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'placeholder': 'Years of Experience'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'placeholder': 'About your farm...', 'rows': 3}), required=False)
    
    license_number = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'License Number'}))
    license_type = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'placeholder': 'License Type (e.g. Trade License)'}))
    issuing_authority = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Issuing Authority'}))
    issue_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    expiry_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    license_document = forms.FileField()

    def clean_license_document(self):
        file = self.cleaned_data.get('license_document')
        if file:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Unsupported file extension. Allowed: JPG, JPEG, PNG, PDF")
            # 5MB limit
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("File size must be under 5MB.")
        return file

