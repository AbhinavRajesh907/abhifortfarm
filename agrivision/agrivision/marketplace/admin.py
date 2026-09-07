from django.contrib import admin

from .models import Cart
from .models import CartItem
from .models import Category
from .models import Order
from .models import OrderItem
from .models import Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "price", "stock", "is_active", "created_at"]
    list_filter = ["category", "is_active"]
    search_fields = ["name"]
    list_editable = ["is_active", "stock", "price"]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "updated_at"]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["cart", "product", "quantity"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product", "quantity", "price", "subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "user",
        "total_amount",
        "payment_method",
        "payment_status",
        "order_status",
        "created_at",
    ]
    list_filter = ["order_status", "payment_status", "payment_method"]
    search_fields = ["order_number", "user__email", "full_name"]
    readonly_fields = ["order_number", "created_at"]
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "product", "quantity", "price", "subtotal"]
