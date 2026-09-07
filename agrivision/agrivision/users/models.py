
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
    
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    username = CharField(_("username"), max_length=150, unique=True)
    phone = CharField(_("Phone Number"), max_length=20, blank=True)
    phone_number = CharField(_("Phone Number (Alt)"), max_length=20, blank=True)
    address = CharField(_("Address"), max_length=255, blank=True)
    street_address = CharField(_("Street Address"), max_length=255, blank=True)
    city = CharField(_("City"), max_length=100, blank=True)
    state = CharField(_("State"), max_length=100, blank=True)
    pincode = CharField(_("Pincode"), max_length=20, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    objects: ClassVar[UserManager] = UserManager()

    def save(self, *args, **kwargs):
        if not self.phone and self.phone_number:
            self.phone = self.phone_number
        elif not self.phone_number and self.phone:
            self.phone_number = self.phone
        if not self.address and self.street_address:
            self.address = self.street_address
        elif not self.street_address and self.address:
            self.street_address = self.address
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})
