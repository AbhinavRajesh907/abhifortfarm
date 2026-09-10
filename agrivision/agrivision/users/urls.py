from django.urls import path

from .views import (
    custom_login_view,
    custom_logout_view,
    user_redirect_view,
    user_detail_view,
    user_update_view,
    register_role_selection_view,
    user_registration_view,
    provider_registration_view,
    user_dashboard_view,
    provider_dashboard_view,
)

app_name = "users"
urlpatterns = [
    # Authentication
    path("login/", view=custom_login_view, name="login"),
    path("logout/", view=custom_logout_view, name="logout"),
    
    # Registration Flow
    path("register/", view=register_role_selection_view, name="register"),
    path("register/user/", view=user_registration_view, name="register_user"),
    path("register/provider/", view=provider_registration_view, name="register_provider"),

    # Dashboards (Teammate integration points)
    path("dashboard/", view=user_dashboard_view, name="user_dashboard"),
    path("provider-dashboard/", view=provider_dashboard_view, name="provider_dashboard"),

    # User Profile & Redirect
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
]
