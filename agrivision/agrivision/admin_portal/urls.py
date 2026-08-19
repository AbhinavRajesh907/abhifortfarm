from django.urls import path
from agrivision.admin_portal import views

app_name = "admin_portal"

urlpatterns = [
    # Dashboard
    path("", views.AdminDashboardView.as_view(), name="dashboard"),
    
    # User Management
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user_detail"),
    path("users/<int:pk>/edit/", views.UserEditView.as_view(), name="user_edit"),
    path("users/<int:pk>/toggle-active/", views.UserToggleActiveView.as_view(), name="user_toggle_active"),
    path("users/<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),
    
    # Provider Management
    path("providers/", views.ProviderListView.as_view(), name="provider_list"),
    path("providers/<int:pk>/", views.ProviderDetailView.as_view(), name="provider_detail"),
    path("providers/<int:pk>/verify-toggle/", views.ProviderVerifyToggleView.as_view(), name="provider_verify_toggle"),
    
    # Provider Request Flow (Admin Review & Approval/Rejection)
    path("provider-requests/", views.ProviderRequestListView.as_view(), name="request_list"),
    path("provider-requests/<int:pk>/", views.ProviderRequestDetailView.as_view(), name="request_detail"),
    path("provider-requests/<int:pk>/approve/", views.ProviderRequestApproveView.as_view(), name="request_approve"),
    path("provider-requests/<int:pk>/reject/", views.ProviderRequestRejectView.as_view(), name="request_reject"),
    
    # Product & Category Management
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("products/create/", views.ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/update/", views.ProductUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/delete/", views.ProductDeleteView.as_view(), name="product_delete"),
    path("products/<int:pk>/toggle-active/", views.ProductToggleActiveView.as_view(), name="product_toggle_active"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/update/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),
    
    # Inventory Management
    path("inventory/", views.InventoryListView.as_view(), name="inventory_list"),
    path("inventory/<int:pk>/adjust/", views.InventoryQuickAdjustView.as_view(), name="inventory_adjust"),
    
    # Order & Payment Management
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path("orders/<int:pk>/update-status/", views.OrderStatusUpdateView.as_view(), name="order_status_update"),
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("payments/<int:pk>/mark-paid/", views.PaymentMarkPaidView.as_view(), name="payment_mark_paid"),
    
    # Business Reports & Data Exports
    path("reports/", views.AdminReportsView.as_view(), name="reports"),
    path("reports/export/sales-csv/", views.ExportSalesReportCSVView.as_view(), name="export_sales_csv"),
    path("reports/export/orders-csv/", views.ExportOrdersReportCSVView.as_view(), name="export_orders_csv"),
    path("reports/export/products-csv/", views.ExportProductsReportCSVView.as_view(), name="export_products_csv"),
]
