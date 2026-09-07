from django.urls import path

from . import views

app_name = "marketplace"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),

    # Cart
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:pk>/", views.update_cart, name="update_cart"),
    path("cart/remove/<int:pk>/", views.remove_from_cart, name="remove_from_cart"),

    # Checkout & Payment
    path("checkout/", views.checkout, name="checkout"),
    path("payment/", views.payment, name="payment"),
    path("place-order/", views.place_order, name="place_order"),

    # Order confirmation & history
    path("order-success/<str:order_number>/", views.order_success, name="order_success"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<str:order_number>/", views.order_detail, name="order_detail"),
]
