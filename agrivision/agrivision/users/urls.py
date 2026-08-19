from django.urls import path

from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view
from .views import register_role_selection_view, user_registration_view, provider_registration_view
from .views import provider_dashboard_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
    path("register/", view=register_role_selection_view, name="register"),
    path("register/user/", view=user_registration_view, name="register_user"),
    path("register/provider/", view=provider_registration_view, name="register_provider"),
    path("provider-dashboard/", view=provider_dashboard_view, name="provider_dashboard"),
]
