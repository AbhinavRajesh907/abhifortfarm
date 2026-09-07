from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, TemplateView, CreateView, RedirectView, UpdateView

from agrivision.users.models import User, ProviderProfile
from agrivision.users.forms import UserLoginForm, UserRegistrationForm, ProviderRegistrationForm

if TYPE_CHECKING:
    from django.db.models import QuerySet


# ==============================================================================
# AUTHENTICATION VIEWS (Clean Username + Password Login / Logout)
# ==============================================================================

class CustomLoginView(View):
    """
    Simplified Username + Password Login View.
    Bypasses MFA/OTP/Authenticators and redirects users to their appropriate dashboard.
    """
    template_name = "users/login.html"
    form_class = UserLoginForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return self.redirect_by_role(request, request.user)
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"].strip()
            password = form.cleaned_data["password"]
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                return self.redirect_by_role(request, user)
            else:
                messages.error(request, _("Invalid username or password."))
        else:
            messages.error(request, _("Invalid username or password."))

        return render(request, self.template_name, {"form": form})

    @staticmethod
    def redirect_by_role(request, user: User):
        """Role-based login redirection logic."""
        if user.is_superuser or user.is_staff or getattr(user, "role", "") == User.Role.ADMIN:
            # Redirect Admin to Santhana's Admin Dashboard
            return redirect("admin_portal:dashboard")
        elif getattr(user, "role", "") == User.Role.PROVIDER:
            profile = getattr(user, "provider_profile", None)
            if profile and getattr(profile, "verification_status", "") == "APPROVED":
                # Redirect Approved Provider to Joyal's Provider Dashboard
                return redirect("providers:dashboard")
            elif profile and getattr(profile, "verification_status", "") == "REJECTED":
                messages.error(request, _("Your provider account application was rejected. Reason: %s") % (getattr(profile, "rejection_reason", "") or _("Verification criteria not met.")))
                return redirect("providers:status")
            else:
                # Pending Provider
                messages.warning(request, _("Your provider account is currently pending admin verification."))
                return redirect("providers:status")
        else:
            # Redirect Normal User to Abinto's User Marketplace Dashboard
            return redirect("marketplace:dashboard")


custom_login_view = CustomLoginView.as_view()


class CustomLogoutView(View):
    """Logs out the user and redirects back to Home page."""
    def get(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, _("You have been signed out."))
        return redirect("home")

    def post(self, request, *args, **kwargs):
        logout(request)
        messages.info(request, _("You have been signed out."))
        return redirect("home")


custom_logout_view = CustomLogoutView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    Global redirect handler for authenticated users based on their role.
    """
    permanent = False

    def get_redirect_url(self) -> str:
        user = self.request.user
        if user.is_superuser or user.is_staff or getattr(user, "role", "") == User.Role.ADMIN:
            return reverse_lazy("admin_portal:dashboard")
        elif getattr(user, "role", "") == User.Role.PROVIDER:
            profile = getattr(user, "provider_profile", None)
            if profile and getattr(profile, "verification_status", "") == "APPROVED":
                return reverse_lazy("providers:dashboard")
            return reverse_lazy("providers:status")
        else:
            return reverse_lazy("marketplace:dashboard")


user_redirect_view = UserRedirectView.as_view()


# ==============================================================================
# REGISTRATION VIEWS (User & Provider Registration)
# ==============================================================================

class RegisterRoleSelectionView(TemplateView):
    """Allows selecting between User and Provider registration."""
    template_name = "users/register_role.html"


register_role_selection_view = RegisterRoleSelectionView.as_view()


class UserRegistrationView(CreateView):
    """
    Normal User Registration View.
    Saves User with role=USER, does NOT auto-login, and redirects to Home with a success message.
    """
    template_name = "users/register_user.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.role = User.Role.USER
        user.save()
        
        messages.success(self.request, _("Registration successful! Please login to continue."))
        return redirect(self.success_url)


user_registration_view = UserRegistrationView.as_view()


class ProviderRegistrationView(CreateView):
    """
    Provider Registration View.
    Saves User with role=PROVIDER, creates ProviderProfile (PENDING status),
    does NOT auto-login, and redirects to Home with verification message.
    """
    template_name = "users/register_provider.html"
    form_class = ProviderRegistrationForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.role = User.Role.PROVIDER
        user.save()
        
        ProviderProfile.objects.create(
            user=user,
            farm_name=form.cleaned_data["farm_name"],
            farm_address=form.cleaned_data["farm_address"],
            provider_type=form.cleaned_data["provider_type"],
            experience_years=form.cleaned_data["experience_years"],
            description=form.cleaned_data.get("description", ""),
            license_number=form.cleaned_data["license_number"],
            license_type=form.cleaned_data["license_type"],
            issuing_authority=form.cleaned_data["issuing_authority"],
            issue_date=form.cleaned_data["issue_date"],
            expiry_date=form.cleaned_data["expiry_date"],
            license_document=form.cleaned_data["license_document"],
            verification_status="PENDING",
        )
        
        messages.success(
            self.request, 
            _("Registration submitted successfully. Your provider account is pending verification. Please login to continue.")
        )
        return redirect(self.success_url)


provider_registration_view = ProviderRegistrationView.as_view()


# ==============================================================================
# DASHBOARD INTEGRATION REDIRECTS / COMPATIBILITY
# ==============================================================================

class UserDashboardPlaceholderView(LoginRequiredMixin, TemplateView):
    """Placeholder view redirecting to Abinto's User Marketplace Dashboard."""
    def get(self, request, *args, **kwargs):
        return redirect("marketplace:dashboard")


user_dashboard_view = UserDashboardPlaceholderView.as_view()


class ProviderDashboardPlaceholderView(LoginRequiredMixin, TemplateView):
    """Placeholder view redirecting to Joyal's Provider Dashboard."""
    def get(self, request, *args, **kwargs):
        return redirect("providers:dashboard")


provider_dashboard_view = ProviderDashboardPlaceholderView.as_view()


# ==============================================================================
# EXISTING USER PROFILE & DETAIL VIEWS
# ==============================================================================

class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


from django.contrib.messages.views import SuccessMessageMixin
from agrivision.users.forms import UserEditProfileForm

class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserEditProfileForm
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated
        return self.request.user


user_update_view = UserUpdateView.as_view()
