from functools import wraps
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect


def admin_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a staff/superuser or admin.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access the AgriVision Admin Management Portal.")
            return redirect("users:login")
        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, "role", "") == "ADMIN"):
            messages.error(request, "Access restricted. You do not have Administrator permissions.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class AdminRequiredMixin(UserPassesTestMixin):
    """
    CBV mixin that verifies the current user has staff or superuser permissions.
    """
    def test_func(self):
        return bool(
            self.request.user.is_authenticated
            and (self.request.user.is_staff or self.request.user.is_superuser or getattr(self.request.user, "role", "") == "ADMIN")
        )

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            messages.warning(self.request, "Please log in with Administrator credentials.")
            return redirect("users:login")
        messages.error(self.request, "Access restricted. Administrator privileges required.")
        return redirect("home")
