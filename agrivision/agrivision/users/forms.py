from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from .models import User


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


class UserEditProfileForm(admin_forms.UserChangeForm):
    password = None  # Explicitly remove password field for profile editing

    class Meta:
        model = User
        fields = [
            "name",
            "username",
            "email",
            "phone_number",
            "street_address",
            "city",
            "state",
            "pincode",
        ]
        labels = {
            "name": _("Full Name"),
            "username": _("Username"),
            "email": _("Email Address"),
            "phone_number": _("Phone Number"),
            "street_address": _("Street Address / Location"),
            "city": _("City"),
            "state": _("State"),
            "pincode": _("Pincode"),
        }
