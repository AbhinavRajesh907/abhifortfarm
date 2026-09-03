from __future__ import annotations

import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .models import Cart
from .models import CartItem
from .models import Category
from .models import Order
from .models import OrderItem
from .models import Product


from django.contrib.auth import get_user_model
User = get_user_model()

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_current_user(request):
    if request.user.is_authenticated:
        return request.user
    user = User.objects.filter(email="joyal@gmail.com").first()
    if not user:
        user = User.objects.first()
        if not user:
            user = User.objects.create(email="joyal@gmail.com")
    return user

def _get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

def dashboard(request):
    user = _get_current_user(request)
    query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()

    products = Product.objects.filter(is_active=True).select_related("category")

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if category_filter:
        products = products.filter(category__name__iexact=category_filter)

    categories = Category.objects.all()
    cart = _get_or_create_cart(user)
    cart_count = cart.get_item_count()

    context = {
        "products": products,
        "categories": categories,
        "query": query,
        "category_filter": category_filter,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/dashboard.html", context)


# ---------------------------------------------------------------------------
# Product listing
# ---------------------------------------------------------------------------

def product_list(request):
    user = _get_current_user(request)
    query = request.GET.get("q", "").strip()
    category_filter = request.GET.get("category", "").strip()

    products = Product.objects.filter(is_active=True).select_related("category")

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if category_filter:
        products = products.filter(category__name__iexact=category_filter)

    categories = Category.objects.all()
    cart = _get_or_create_cart(user)
    cart_count = cart.get_item_count()

    context = {
        "products": products,
        "categories": categories,
        "query": query,
        "category_filter": category_filter,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/product_list.html", context)


# ---------------------------------------------------------------------------
# Product detail
# ---------------------------------------------------------------------------

def product_detail(request, pk):
    user = _get_current_user(request)
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = _get_or_create_cart(user)
    cart_count = cart.get_item_count()

    context = {
        "product": product,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/product_detail.html", context)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

def cart_view(request):
    user = _get_current_user(request)
    cart = _get_or_create_cart(user)
    items = cart.items.select_related("product", "product__category").all()
    total = cart.get_total()
    cart_count = cart.get_item_count()

    context = {
        "cart": cart,
        "items": items,
        "total": total,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/cart.html", context)


def add_to_cart(request, pk):
    if request.method == "POST":
        user = _get_current_user(request)
        product = get_object_or_404(Product, pk=pk, is_active=True)
        quantity = int(request.POST.get("quantity", 1))
        quantity = max(1, min(quantity, product.stock))  # clamp to valid range

        cart = _get_or_create_cart(user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            new_qty = cart_item.quantity + quantity
            cart_item.quantity = min(new_qty, product.stock)
        else:
            cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"'{product.name}' added to your cart.")
    return redirect("marketplace:cart")


def update_cart(request, pk):
    if request.method == "POST":
        user = _get_current_user(request)
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=user)
        quantity = int(request.POST.get("quantity", 1))
        if quantity < 1:
            cart_item.delete()
            messages.info(request, "Item removed from cart.")
        else:
            cart_item.quantity = min(quantity, cart_item.product.stock)
            cart_item.save()
    return redirect("marketplace:cart")


def remove_from_cart(request, pk):
    if request.method == "POST":
        user = _get_current_user(request)
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=user)
        product_name = cart_item.product.name
        cart_item.delete()
        messages.info(request, f"'{product_name}' removed from cart.")
    return redirect("marketplace:cart")


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

def checkout(request):
    user = _get_current_user(request)
    cart = _get_or_create_cart(user)
    items = cart.items.select_related("product").all()

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("marketplace:cart")

    total = cart.get_total()
    cart_count = cart.get_item_count()

    # Pre-fill form fields from user profile if available
    initial_name = getattr(user, "name", "") or ""
    initial_email = user.email

    if request.method == "POST":
        # Validate required fields
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        delivery_address = request.POST.get("delivery_address", "").strip()
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        pin_code = request.POST.get("pin_code", "").strip()

        if not all([full_name, phone, email, delivery_address, city, district, pin_code]):
            messages.error(request, "Please fill in all delivery details.")
        else:
            # Save delivery info to session for the payment step
            request.session["checkout_data"] = {
                "full_name": full_name,
                "phone": phone,
                "email": email,
                "delivery_address": delivery_address,
                "city": city,
                "district": district,
                "pin_code": pin_code,
            }
            return redirect("marketplace:payment")

    context = {
        "items": items,
        "total": total,
        "cart_count": cart_count,
        "initial_name": initial_name,
        "initial_email": initial_email,
    }
    return render(request, "marketplace/checkout.html", context)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

def payment(request):
    user = _get_current_user(request)
    checkout_data = request.session.get("checkout_data")
    if not checkout_data:
        messages.warning(request, "Please complete delivery details first.")
        return redirect("marketplace:checkout")

    cart = _get_or_create_cart(user)
    items = cart.items.select_related("product").all()

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("marketplace:cart")

    total = cart.get_total()
    cart_count = cart.get_item_count()

    context = {
        "items": items,
        "total": total,
        "cart_count": cart_count,
        "checkout_data": checkout_data,
    }
    return render(request, "marketplace/payment.html", context)


# ---------------------------------------------------------------------------
# Place order
# ---------------------------------------------------------------------------

def place_order(request):
    if request.method != "POST":
        return redirect("marketplace:payment")

    user = _get_current_user(request)
    checkout_data = request.session.get("checkout_data")
    if not checkout_data:
        messages.warning(request, "Session expired. Please start checkout again.")
        return redirect("marketplace:checkout")

    cart = _get_or_create_cart(user)
    items = cart.items.select_related("product").all()

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("marketplace:cart")

    payment_method = request.POST.get("payment_method", "cod")
    if payment_method not in ["cod", "online"]:
        payment_method = "cod"

    # Generate unique order number
    order_number = "AGV" + uuid.uuid4().hex[:8].upper()

    total = cart.get_total()

    # Create Order
    order = Order.objects.create(
        user=user,
        order_number=order_number,
        total_amount=total,
        full_name=checkout_data["full_name"],
        phone=checkout_data["phone"],
        email=checkout_data["email"],
        delivery_address=checkout_data["delivery_address"],
        city=checkout_data["city"],
        district=checkout_data["district"],
        pin_code=checkout_data["pin_code"],
        payment_method=payment_method,
        payment_status=Order.PENDING,
        order_status=Order.ORDER_PENDING,
    )

    # Create OrderItems and deduct stock
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price,
            subtotal=item.get_subtotal(),
        )
        # Deduct stock
        product = item.product
        product.stock = max(0, product.stock - item.quantity)
        product.save(update_fields=["stock"])

    # Clear cart
    cart.items.all().delete()

    # Clear session checkout data
    del request.session["checkout_data"]

    messages.success(request, f"Order #{order_number} placed successfully!")
    return redirect("marketplace:order_success", order_number=order_number)


# ---------------------------------------------------------------------------
# Order confirmation
# ---------------------------------------------------------------------------

def order_success(request, order_number):
    user = _get_current_user(request)
    order = get_object_or_404(Order, order_number=order_number, user=user)
    cart = _get_or_create_cart(user)
    cart_count = cart.get_item_count()

    context = {
        "order": order,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/order_success.html", context)


# ---------------------------------------------------------------------------
# My Orders
# ---------------------------------------------------------------------------

def my_orders(request):
    user = _get_current_user(request)
    orders = Order.objects.filter(user=user).order_by("-created_at")
    cart = _get_or_create_cart(user)
    cart_count = cart.get_item_count()

    context = {
        "orders": orders,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/orders.html", context)


# ---------------------------------------------------------------------------
# Order detail
# ---------------------------------------------------------------------------

def order_detail(request, order_number):
    user = _get_current_user(request)
    order = get_object_or_404(Order, order_number=order_number, user=user)
    order_items = order.items.select_related("product").all()
    cart = _get_or_create_cart(user)
    cart_count = cart.get_item_count()

    context = {
        "order": order,
        "order_items": order_items,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/order_detail.html", context)
