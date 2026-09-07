from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import User
from agrivision.providers.models import ProviderProfile


class ProviderProfileInline(admin.StackedInline):
    model = ProviderProfile
    can_delete = False
    verbose_name_plural = _("Provider Profile")
    fk_name = "user"


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    inlines = [ProviderProfileInline]
    
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("name", "email", "phone", "address", "city", "state", "pincode")}),
        (_("Role & Access"), {"fields": ("role",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["username", "email", "name", "role", "is_staff", "is_superuser"]
    list_filter = ["role", "is_staff", "is_superuser", "is_active"]
    search_fields = ["username", "name", "email", "phone"]
    ordering = ["id"]
