from django import forms
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from .models import User, ProviderProfile


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
        field_classes = {"email": EmailField}
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
            "email": {"unique": _("This email has already been taken.")},
        }


class UserLoginForm(forms.Form):
    """Simple Username + Password Login Form."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username',
            'class': 'form-control form-control-lg',
            'autocomplete': 'username',
            'autofocus': True,
        }),
        label=_("Username"),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'class': 'form-control form-control-lg',
            'autocomplete': 'current-password',
        }),
        label=_("Password"),
    )


<<<<<<< HEAD
class BaseRegistrationForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Full Name', 'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=150, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Choose Username', 'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=20, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number', 'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password (min. 8 characters)', 'class': 'form-control'}), 
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-control'}), 
        required=True
    )
    address = forms.CharField(
        max_length=255, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Street Address / Location', 'class': 'form-control'})
    )
    city = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'City', 'class': 'form-control'})
    )
    state = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'State', 'class': 'form-control'})
    )
    pincode = forms.CharField(
        max_length=20, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'Pincode', 'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['name', 'username', 'email', 'phone', 'address', 'city', 'state', 'pincode']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(_("A user with that username already exists."))
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("A user with that email already exists."))
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and len(password) < 6:
            raise forms.ValidationError(_("Password must be at least 6 characters long."))
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', _("Passwords do not match."))
        
        return cleaned_data


class UserRegistrationForm(BaseRegistrationForm):
    """Registration form for Normal Users."""
    pass


class ProviderRegistrationForm(BaseRegistrationForm):
    """Registration form for Agricultural Providers."""
    # Farm / Business Details
    farm_name = forms.CharField(
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Farm or Business Name', 'class': 'form-control'})
    )
    provider_type = forms.ChoiceField(
        choices=[
            ('Plant Nursery', 'Plant Nursery'),
            ('Seed Supplier', 'Seed Supplier'),
            ('Farmer', 'Farmer'),
            ('Agricultural Farm', 'Agricultural Farm'),
            ('Gardening Supplier', 'Gardening Supplier'),
            ('Other', 'Other'),
        ],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    farm_address = forms.CharField(
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Farm / Facility Location Address', 'class': 'form-control'})
    )
    experience_years = forms.CharField(
        max_length=50, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. 5 Years', 'class': 'form-control'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Tell us briefly about your agricultural products or farm...', 'rows': 3, 'class': 'form-control'}), 
        required=False
    )
    
    # License Information
    license_number = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'License / Registration Number', 'class': 'form-control'})
    )
    license_type = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'License Type (e.g. Trade License, Seed Dealer License)', 'class': 'form-control'})
    )
    issuing_authority = forms.CharField(
        max_length=255, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Issuing Authority (e.g. Dept of Agriculture)', 'class': 'form-control'})
    )
    issue_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    expiry_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    license_document = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.jpg,.jpeg,.png,.pdf'})
    )

    def clean_license_document(self):
        file = self.cleaned_data.get('license_document')
        if file:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
            import os
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError(_("Unsupported file extension. Allowed: JPG, JPEG, PNG, PDF"))
            # 5MB limit
            if file.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_("File size must be under 5MB."))
        return file


class UserEditProfileForm(admin_forms.UserChangeForm):
    password = None  # Explicitly remove password field for profile editing

    class Meta:
        model = User
        fields = [
            "name",
            "username",
            "email",
            "phone",
            "phone_number",
            "address",
            "street_address",
            "city",
            "state",
            "pincode",
        ]
        labels = {
            "name": _("Full Name"),
            "username": _("Username"),
            "email": _("Email Address"),
            "phone": _("Phone Number"),
            "phone_number": _("Alternate Phone"),
            "address": _("Address"),
            "street_address": _("Street Address / Location"),
            "city": _("City"),
            "state": _("State"),
            "pincode": _("Pincode"),
        }
