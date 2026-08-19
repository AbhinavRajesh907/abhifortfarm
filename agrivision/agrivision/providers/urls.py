from django.urls import path
from . import views

app_name = "providers"
urlpatterns = [
    path("dashboard/", views.ProviderDashboardView.as_view(), name="dashboard"),
    path("profile/edit/", views.ProviderProfileUpdateView.as_view(), name="profile_edit"),
    path("requests/new/", views.ProviderRequestCreateView.as_view(), name="request_new"),
]
