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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
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
    cart = _get_or_create_cart(request.user)
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

@login_required
def product_list(request):
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
    cart = _get_or_create_cart(request.user)
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

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()

    context = {
        "product": product,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/product_detail.html", context)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@login_required
def cart_view(request):
    cart = _get_or_create_cart(request.user)
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


@login_required
def add_to_cart(request, pk):
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk, is_active=True)
        quantity = int(request.POST.get("quantity", 1))
        quantity = max(1, min(quantity, product.stock))  # clamp to valid range

        cart = _get_or_create_cart(request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            new_qty = cart_item.quantity + quantity
            cart_item.quantity = min(new_qty, product.stock)
        else:
            cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"'{product.name}' added to your cart.")
    return redirect("marketplace:cart")


@login_required
def update_cart(request, pk):
    if request.method == "POST":
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        quantity = int(request.POST.get("quantity", 1))
        if quantity < 1:
            cart_item.delete()
            messages.info(request, "Item removed from cart.")
        else:
            cart_item.quantity = min(quantity, cart_item.product.stock)
            cart_item.save()
    return redirect("marketplace:cart")


@login_required
def remove_from_cart(request, pk):
    if request.method == "POST":
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        product_name = cart_item.product.name
        cart_item.delete()
        messages.info(request, f"'{product_name}' removed from cart.")
    return redirect("marketplace:cart")


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------

@login_required
def checkout(request):
    cart = _get_or_create_cart(request.user)
    items = cart.items.select_related("product", "product__provider").all()

    if not items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("marketplace:cart")

    total = cart.get_total()
    cart_count = cart.get_item_count()
    user = request.user

    # Group items by provider for summary display
    grouped_items = {}
    for item in items:
        provider = item.product.provider
        if provider not in grouped_items:
            grouped_items[provider] = {"items": [], "subtotal": 0}
        grouped_items[provider]["items"].append(item)
        grouped_items[provider]["subtotal"] += item.get_subtotal()

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
        "grouped_items": grouped_items,
        "total": total,
        "cart_count": cart_count,
        "initial_name": initial_name,
        "initial_email": initial_email,
    }
    return render(request, "marketplace/checkout.html", context)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

@login_required
def payment(request):
    checkout_data = request.session.get("checkout_data")
    if not checkout_data:
        messages.warning(request, "Please complete delivery details first.")
        return redirect("marketplace:checkout")

    cart = _get_or_create_cart(request.user)
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

@login_required
def place_order(request):
    if request.method != "POST":
        return redirect("marketplace:payment")

    checkout_data = request.session.get("checkout_data")
    if not checkout_data:
        messages.warning(request, "Session expired. Please start checkout again.")
        return redirect("marketplace:checkout")

    cart = _get_or_create_cart(request.user)
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
        user=request.user,
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

@login_required
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()

    context = {
        "order": order,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/order_success.html", context)


# ---------------------------------------------------------------------------
# My Orders
# ---------------------------------------------------------------------------

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()

    context = {
        "orders": orders,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/orders.html", context)


# ---------------------------------------------------------------------------
# Order detail
# ---------------------------------------------------------------------------

@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("product").all()
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()

    context = {
        "order": order,
        "order_items": order_items,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/order_detail.html", context)
