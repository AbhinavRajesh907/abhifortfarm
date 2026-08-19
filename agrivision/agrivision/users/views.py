from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, TemplateView, CreateView
from django.views.generic import RedirectView
from django.views.generic import UpdateView
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy

from agrivision.users.models import User, ProviderProfile
from agrivision.users.forms import UserRegistrationForm, ProviderRegistrationForm

if TYPE_CHECKING:
    from django.db.models import QuerySet


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.request.user.pk})


user_redirect_view = UserRedirectView.as_view()


class RegisterRoleSelectionView(TemplateView):
    template_name = "users/register_role.html"


register_role_selection_view = RegisterRoleSelectionView.as_view()


class UserRegistrationView(CreateView):
    template_name = "users/register_user.html"
    form_class = UserRegistrationForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.role = User.Role.USER
        user.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(self.success_url)


user_registration_view = UserRegistrationView.as_view()


class ProviderRegistrationView(CreateView):
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
            description=form.cleaned_data["description"],
            license_number=form.cleaned_data["license_number"],
            license_type=form.cleaned_data["license_type"],
            issuing_authority=form.cleaned_data["issuing_authority"],
            issue_date=form.cleaned_data["issue_date"],
            expiry_date=form.cleaned_data["expiry_date"],
            license_document=form.cleaned_data["license_document"],
            verification_status=ProviderProfile.VerificationStatus.PENDING
        )
        
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(self.success_url)


provider_registration_view = ProviderRegistrationView.as_view()

class ProviderDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "users/provider_dashboard_placeholder.html"

    def test_func(self):
        return self.request.user.role == User.Role.PROVIDER

provider_dashboard_view = ProviderDashboardView.as_view()
