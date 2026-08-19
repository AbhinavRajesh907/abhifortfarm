
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import TextChoices
from django.db.models import OneToOneField
from django.db.models import CASCADE
from django.db.models import DateField
from django.db.models import FileField
from django.db.models import TextField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for agrivision.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class Role(TextChoices):
        USER = "USER", _("User")
        PROVIDER = "PROVIDER", _("Provider")
        ADMIN = "ADMIN", _("Admin")

    role = CharField(_("Role"), max_length=20, choices=Role.choices, default=Role.USER)
    phone = CharField(_("Phone Number"), max_length=20, blank=True)
    address = CharField(_("Address"), max_length=255, blank=True)
    city = CharField(_("City"), max_length=100, blank=True)
    state = CharField(_("State"), max_length=100, blank=True)
    pincode = CharField(_("Pincode"), max_length=20, blank=True)
    
    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    # We will use email for authentication, but allow a username for profile display.
    username = CharField(_("username"), max_length=150, unique=True, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

from django.db import models

class ProviderProfile(models.Model):
    class VerificationStatus(TextChoices):
        PENDING = "PENDING", _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    user = OneToOneField(User, on_delete=CASCADE, related_name="provider_profile")
    farm_name = CharField(_("Farm/Business Name"), max_length=255)
    farm_address = CharField(_("Farm Address"), max_length=255)
    provider_type = CharField(_("Type of Provider"), max_length=100)
    experience_years = CharField(_("Years of Experience"), max_length=50)
    description = TextField(_("Description"), blank=True)
    
    # License Details
    license_number = CharField(_("License Number"), max_length=100)
    license_type = CharField(_("License Type"), max_length=100)
    issuing_authority = CharField(_("Issuing Authority"), max_length=255)
    issue_date = DateField(_("Issue Date"), null=True, blank=True)
    expiry_date = DateField(_("Expiry Date"), null=True, blank=True)
    license_document = FileField(_("License Document"), upload_to="licenses/")
    
    # Verification Status
    verification_status = CharField(
        _("Verification Status"), 
        max_length=20, 
        choices=VerificationStatus.choices, 
        default=VerificationStatus.PENDING
    )
    rejection_reason = TextField(_("Rejection Reason"), blank=True)

    def __str__(self):
        return f"{self.farm_name} ({self.user.email})"
