from django.urls import path

from . import views

app_name = "providers"

urlpatterns = [
    # ── Any authenticated user ──────────────────────────────────────────────
    # Apply to become a provider
    path("apply/", views.provider_apply, name="apply"),
    # View current application status (pending / rejected)
    path("status/", views.provider_status, name="status"),

    # ── Approved Providers only ─────────────────────────────────────────────
    # Main dashboard
    path("dashboard/", views.provider_dashboard, name="dashboard"),
    # Profile management
    path("profile/edit/", views.provider_profile_edit, name="profile_edit"),
    # Product management
    path("products/", views.provider_product_list, name="product_list"),
    path("products/add/", views.provider_product_add, name="product_add"),
    path("products/<int:pk>/edit/", views.provider_product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.provider_product_delete, name="product_delete"),
    # Orders related to provider's products
    path("orders/", views.provider_orders, name="orders"),
    path("orders/view/", views.provider_orders_view, name="orders_view"),
    path("orders/<int:order_id>/status/", views.provider_order_status_update, name="order_status_update"),
]
