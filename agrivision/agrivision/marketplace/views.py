from __future__ import annotations

import re
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone

from .models import Cart
from .models import CartItem
from .models import Category
from .models import Order
from .models import OrderItem
from .models import Payment
from .models import Product
from .models import RefundRequest
from .models import StockHistory


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

    products = Product.objects.filter(is_active=True).select_related("category", "provider")

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if category_filter:
        products = products.filter(
            Q(category__name__iexact=category_filter)
            | Q(category__parent__name__iexact=category_filter)
            | Q(category__category_type__iexact=category_filter)
        )

    categories = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related("subcategories")
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

    products = Product.objects.filter(is_active=True).select_related("category", "provider")

    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    if category_filter:
        products = products.filter(
            Q(category__name__iexact=category_filter)
            | Q(category__parent__name__iexact=category_filter)
            | Q(category__category_type__iexact=category_filter)
        )

    categories = Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related("subcategories")
    all_subcategories = Category.objects.filter(is_active=True, parent__isnull=False)
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()

    context = {
        "products": products,
        "categories": categories,
        "all_subcategories": all_subcategories,
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
    product = get_object_or_404(Product.objects.select_related("category", "provider"), pk=pk, is_active=True)
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()
    cart_item = cart.items.filter(product=product).first()
    cart_item_qty = cart_item.quantity if cart_item else 0
    remaining_stock = max(0, product.stock - cart_item_qty)

    context = {
        "product": product,
        "cart_count": cart_count,
        "cart_item_qty": cart_item_qty,
        "remaining_stock": remaining_stock,
    }
    return render(request, "marketplace/product_detail.html", context)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@login_required
def cart_view(request):
    cart = _get_or_create_cart(request.user)
    items = cart.items.select_related("product", "product__category", "product__provider").all()
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

        # 1. Parse and strictly validate input quantity
        raw_quantity = request.POST.get("quantity", "1").strip()
        try:
            quantity = int(raw_quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid positive whole number for quantity.")
            return redirect("marketplace:product_detail", pk=pk)

        # 2. Check if product is out of stock
        if product.stock <= 0:
            messages.error(request, f"Sorry, '{product.name}' is currently out of stock.")
            return redirect("marketplace:product_detail", pk=pk)

        # 3. Check requested quantity against total stock
        if quantity > product.stock:
            messages.error(
                request,
                f"Only {product.stock} unit{'s are' if product.stock != 1 else ' is'} available. Please enter a quantity of {product.stock} or less."
            )
            return redirect("marketplace:product_detail", pk=pk)

        # 4. Check against existing items in user's cart
        cart = _get_or_create_cart(request.user)
        cart_item = cart.items.filter(product=product).first()
        current_cart_qty = cart_item.quantity if cart_item else 0
        new_total_qty = current_cart_qty + quantity

        if new_total_qty > product.stock:
            remaining_allowance = product.stock - current_cart_qty
            if remaining_allowance <= 0:
                messages.error(
                    request,
                    f"Only {product.stock} unit{'s are' if product.stock != 1 else ' is'} available. You already have all {product.stock} in your cart."
                )
            else:
                messages.error(
                    request,
                    f"Only {product.stock} unit{'s are' if product.stock != 1 else ' is'} available ({current_cart_qty} already in your cart). You can add at most {remaining_allowance} more."
                )
            return redirect("marketplace:product_detail", pk=pk)

        if cart_item:
            cart_item.quantity = new_total_qty
            cart_item.save(update_fields=["quantity"])
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=quantity)

        messages.success(request, f"'{product.name}' (Qty: {quantity}) added to your cart.")
    return redirect("marketplace:cart")


@login_required
def update_cart(request, pk):
    if request.method == "POST":
        cart_item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        raw_quantity = request.POST.get("quantity", "1").strip()
        try:
            quantity = int(raw_quantity)
        except (ValueError, TypeError):
            messages.error(request, "Invalid quantity entered.")
            return redirect("marketplace:cart")

        if quantity < 1:
            product_name = cart_item.product.name
            cart_item.delete()
            messages.info(request, f"'{product_name}' removed from cart.")
        else:
            if quantity > cart_item.product.stock:
                messages.error(
                    request,
                    f"Only {cart_item.product.stock} unit{'s are' if cart_item.product.stock != 1 else ' is'} available for '{cart_item.product.name}'. Please enter a quantity of {cart_item.product.stock} or less."
                )
            else:
                cart_item.quantity = quantity
                cart_item.save(update_fields=["quantity"])
                messages.success(request, f"Updated quantity for '{cart_item.product.name}' to {quantity}.")
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
        return redirect("marketplace:product_list")

    # Validate all cart items against current database stock before proceeding
    stock_errors = []
    for item in items:
        if item.product.stock <= 0:
            stock_errors.append(f"'{item.product.name}' is currently out of stock.")
        elif item.quantity > item.product.stock:
            stock_errors.append(
                f"Only {item.product.stock} unit{'s are' if item.product.stock != 1 else ' is'} available for '{item.product.name}'. (In cart: {item.quantity})"
            )

    if stock_errors:
        for err in stock_errors:
            messages.error(request, err)
        messages.warning(request, "Please adjust the item quantities in your cart before proceeding to checkout.")
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
    initial_email = user.email or ""
    initial_phone = getattr(user, "phone_number", "") or getattr(user, "phone", "") or ""
    initial_address = getattr(user, "street_address", "") or getattr(user, "address", "") or ""
    initial_city = getattr(user, "city", "") or ""
    initial_district = getattr(user, "state", "") or ""
    initial_pincode = getattr(user, "pincode", "") or ""

    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        delivery_address = request.POST.get("delivery_address", "").strip()
        city = request.POST.get("city", "").strip()
        district = request.POST.get("district", "").strip()
        pin_code = request.POST.get("pin_code", "").strip()

        # Update initial values with submitted data so form retains input on validation errors
        initial_name = full_name
        initial_phone = phone
        initial_email = email
        initial_address = delivery_address
        initial_city = city
        initial_district = district
        initial_pincode = pin_code

        validation_errors = []

        if not full_name:
            validation_errors.append("Please enter your full name.")
        elif not re.match(r"^[a-zA-Z\s.'-]+$", full_name):
            validation_errors.append("Full name should only contain alphabetic characters and spaces.")
        elif len(full_name) < 2:
            validation_errors.append("Full name must be at least 2 characters long.")

        if not phone:
            validation_errors.append("Please enter your contact phone number.")
        elif not re.match(r"^[6-9]\d{9}$", phone):
            validation_errors.append("Please enter a valid 10-digit mobile number (numbers only, e.g. 9876543210).")

        if not email:
            validation_errors.append("Please enter your email address.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                validation_errors.append("Please enter a valid email address.")

        if not delivery_address:
            validation_errors.append("Please enter your delivery street address.")
        elif len(delivery_address) < 5:
            validation_errors.append("Please enter a detailed delivery address (at least 5 characters).")

        if not city:
            validation_errors.append("Please enter your delivery city / town.")
        elif not re.match(r"^[a-zA-Z\s.-]+$", city):
            validation_errors.append("City name should only contain alphabetic characters.")

        if not district:
            validation_errors.append("Please enter your district / state.")
        elif not re.match(r"^[a-zA-Z\s.-]+$", district):
            validation_errors.append("District / State name should only contain alphabetic characters.")

        if not pin_code:
            validation_errors.append("Please enter your 6-digit postal PIN code.")
        elif not re.match(r"^\d{6}$", pin_code):
            validation_errors.append("PIN code must be exactly 6 digits (numbers only, e.g. 682001).")

        if validation_errors:
            for error_msg in validation_errors:
                messages.error(request, error_msg)
        else:
            # Store in session and move to payment step
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
        "initial_phone": initial_phone,
        "initial_address": initial_address,
        "initial_city": initial_city,
        "initial_district": initial_district,
        "initial_pincode": initial_pincode,
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
        return redirect("marketplace:product_list")

    # Re-verify stock before rendering payment page
    for item in items:
        if item.product.stock <= 0 or item.quantity > item.product.stock:
            messages.error(
                request,
                f"Stock availability changed for '{item.product.name}'. Available: {item.product.stock}. Please adjust your cart."
            )
            return redirect("marketplace:cart")

    total = cart.get_total()
    cart_count = cart.get_item_count()

    half_online = (total / Decimal("2.00")).quantize(Decimal("0.01"))
    half_cod = total - half_online

    context = {
        "checkout_data": checkout_data,
        "items": items,
        "total": total,
        "half_online": half_online,
        "half_cod": half_cod,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/payment.html", context)


# ---------------------------------------------------------------------------
# Place order (Supporting 3-tier Payment & Atomic Stock History)
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
    items = list(cart.items.select_related("product", "product__provider").all())

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("marketplace:product_list")

    payment_method = request.POST.get("payment_method", Order.COD)
    total = cart.get_total()

    # Determine 3-tier payment amounts & initial pending statuses awaiting provider confirmation
    if payment_method == Order.ONLINE:
        online_paid_amount = total
        cod_amount_due = Decimal("0.00")
        payment_status = Order.PENDING
        order_status = Order.ORDER_PENDING
    elif payment_method == Order.HALF_COD:
        online_paid_amount = (total / Decimal("2.00")).quantize(Decimal("0.01"))
        cod_amount_due = total - online_paid_amount
        payment_status = Order.PENDING
        order_status = Order.ORDER_PENDING
    else:  # Full COD
        payment_method = Order.COD
        online_paid_amount = Decimal("0.00")
        cod_amount_due = total
        payment_status = Order.PENDING
        order_status = Order.ORDER_PENDING

    # Database transaction with row-level locks on products to prevent race conditions
    try:
        with transaction.atomic():
            # Lock the products in the database
            product_ids = [item.product_id for item in items]
            locked_products = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }

            # 1. Final server-side stock verification under database lock
            for item in items:
                locked_product = locked_products.get(item.product_id)
                if not locked_product or locked_product.stock < item.quantity:
                    avail = locked_product.stock if locked_product else 0
                    if avail <= 0:
                        raise ValueError(f"Sorry, '{item.product.name}' just went out of stock.")
                    else:
                        raise ValueError(
                            f"Only {avail} unit{'s are' if avail != 1 else ' is'} available for '{item.product.name}'. Please enter a quantity of {avail} or less."
                        )

            # Generate unique order number
            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

            # 2. Create Order
            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                total_amount=total,
                online_paid_amount=online_paid_amount,
                cod_amount_due=cod_amount_due,
                full_name=checkout_data["full_name"],
                phone=checkout_data["phone"],
                email=checkout_data["email"],
                delivery_address=checkout_data["delivery_address"],
                city=checkout_data["city"],
                district=checkout_data["district"],
                pin_code=checkout_data["pin_code"],
                payment_method=payment_method,
                payment_status=payment_status,
                order_status=order_status,
            )

            # Create Payment record for auditing
            Payment.objects.create(
                order=order,
                user=request.user,
                payment_method=payment_method,
                amount=online_paid_amount if online_paid_amount > 0 else total,
                status=payment_status,
            )

            # 3. Create OrderItems & safely decrement stock + log stock history
            for item in items:
                locked_product = locked_products[item.product_id]
                prev_stock = locked_product.stock
                new_stock = max(0, prev_stock - item.quantity)

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    provider=locked_product.provider,
                    provider_user=locked_product.provider_user,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price,
                    subtotal=item.get_subtotal(),
                )

                # Deduct stock and save
                locked_product.stock = new_stock
                locked_product.save(update_fields=["stock"])

                # Log Stock History
                StockHistory.objects.create(
                    product=locked_product,
                    provider=locked_product.provider,
                    previous_stock=prev_stock,
                    quantity_changed=-item.quantity,
                    new_stock=new_stock,
                    change_type=StockHistory.ChangeType.ORDER,
                    reason=f"Order #{order_number} placed by {request.user.email}",
                    related_order=order,
                    created_by=request.user,
                )

            # 4. Clear cart
            cart.items.all().delete()

    except ValueError as stock_err:
        messages.error(request, str(stock_err))
        return redirect("marketplace:cart")

    if "checkout_data" in request.session:
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
# My Orders & Order Detail
# ---------------------------------------------------------------------------

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items", "refund_requests").order_by("-created_at")
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()

    context = {
        "orders": orders,
        "cart_count": cart_count,
    }
    return render(request, "marketplace/orders.html", context)


def _get_order_stage_info(order):
    status_progression = {
        Order.ORDER_PENDING: {
            "step": 1,
            "percent": 20,
            "label": "Order Placed & Awaiting Confirmation",
            "badge_class": "bg-warning text-dark",
            "icon": "bi-bag-check",
            "desc": "Order submitted! The farm provider will verify inventory and confirm/process your order before dispatch.",
        },
        Order.CONFIRMED: {
            "step": 2,
            "percent": 40,
            "label": "Confirmed by Provider",
            "badge_class": "bg-info text-dark",
            "icon": "bi-check2-circle",
            "desc": "The provider has verified nursery stock and accepted fulfillment. Payment and preparation are active.",
        },
        Order.PROCESSING: {
            "step": 3,
            "percent": 65,
            "label": "Packing & Quality Prep",
            "badge_class": "bg-primary",
            "icon": "bi-box-seam",
            "desc": "Your seeds / saplings are being carefully packed in temperature-controlled nursery crates.",
        },
        Order.SHIPPED: {
            "step": 4,
            "percent": 85,
            "label": "Out for Delivery / In Transit",
            "badge_class": "bg-primary",
            "icon": "bi-truck",
            "desc": "Your package is on its way to your delivery address with our courier partner.",
        },
        Order.DELIVERED: {
            "step": 5,
            "percent": 100,
            "label": "Delivered & Balance Settled",
            "badge_class": "bg-success",
            "icon": "bi-house-check",
            "desc": "Package delivered to your doorstep! Any remaining 50% Cash on Delivery balance was collected upon delivery.",
        },
        Order.CANCELLED: {
            "step": 0,
            "percent": 0,
            "label": "Order Cancelled",
            "badge_class": "bg-danger",
            "icon": "bi-x-circle",
            "desc": f"This order was cancelled. Reason: {order.cancellation_reason or 'Customer cancellation'}.",
        },
        Order.REFUND_REQUESTED: {
            "step": 5,
            "percent": 100,
            "label": "Refund Requested",
            "badge_class": "bg-warning text-dark",
            "icon": "bi-arrow-counterclockwise",
            "desc": "Your return/refund claim is currently under review by our Admin team.",
        },
        Order.REFUNDED: {
            "step": 5,
            "percent": 100,
            "label": "Refund Completed",
            "badge_class": "bg-secondary",
            "icon": "bi-check-all",
            "desc": "Refund approved and payment reversed.",
        },
    }
    return status_progression.get(
        order.order_status,
        {"step": 1, "percent": 20, "label": order.get_order_status_display(), "badge_class": "bg-secondary", "icon": "bi-info-circle", "desc": ""}
    )


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("product", "product__category", "product__provider").all()
    refund_requests = order.refund_requests.all().order_by("-created_at")
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()
    current_stage = _get_order_stage_info(order)

    context = {
        "order": order,
        "order_items": order_items,
        "refund_requests": refund_requests,
        "refund_reasons": RefundRequest.ReasonChoices.choices,
        "cart_count": cart_count,
        "current_stage": current_stage,
    }
    return render(request, "marketplace/order_detail.html", context)


@login_required
def track_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    order_items = order.items.select_related("product", "product__category", "product__provider").all()
    cart = _get_or_create_cart(request.user)
    cart_count = cart.get_item_count()
    current_stage = _get_order_stage_info(order)

    context = {
        "order": order,
        "order_items": order_items,
        "cart_count": cart_count,
        "current_stage": current_stage,
    }
    return render(request, "marketplace/order_track.html", context)


# ---------------------------------------------------------------------------
# Order Cancellation (Pre-dispatch Stock Restoration)
# ---------------------------------------------------------------------------

@login_required
def cancel_order(request, order_number):
    if request.method != "POST":
        return redirect("marketplace:order_detail", order_number=order_number)

    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if not order.can_cancel:
        messages.error(request, "This order cannot be cancelled as it has already been processed or dispatched.")
        return redirect("marketplace:order_detail", order_number=order_number)

    reason = request.POST.get("cancellation_reason", "Cancelled by customer").strip()

    with transaction.atomic():
        order.order_status = Order.CANCELLED
        order.cancellation_reason = reason
        order.cancelled_at = timezone.now()
        if order.payment_status in [Order.PAID, Order.PARTIALLY_PAID]:
            order.payment_status = Order.REFUNDED
        order.save()

        # Restock products and log StockHistory
        for item in order.items.select_related("product").all():
            if item.product:
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                prev_stock = product.stock
                new_stock = prev_stock + item.quantity
                product.stock = new_stock
                product.save(update_fields=["stock"])

                StockHistory.objects.create(
                    product=product,
                    provider=product.provider,
                    previous_stock=prev_stock,
                    quantity_changed=item.quantity,
                    new_stock=new_stock,
                    change_type=StockHistory.ChangeType.CANCELLATION,
                    reason=f"Order #{order.order_number} cancelled by customer: {reason}",
                    related_order=order,
                    created_by=request.user,
                )

    messages.success(request, f"Order #{order.order_number} has been cancelled and stock has been restored.")
    return redirect("marketplace:order_detail", order_number=order_number)


# ---------------------------------------------------------------------------
# Refund Request Workflow
# ---------------------------------------------------------------------------

@login_required
def request_refund(request, order_number):
    if request.method != "POST":
        return redirect("marketplace:order_detail", order_number=order_number)

    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    if not order.can_request_refund:
        messages.error(request, "This order is not currently eligible for a refund request.")
        return redirect("marketplace:order_detail", order_number=order_number)

    reason = request.POST.get("reason", RefundRequest.ReasonChoices.DAMAGED)
    custom_reason = request.POST.get("custom_reason", "").strip()
    additional_desc = request.POST.get("additional_description", "").strip()

    if reason == RefundRequest.ReasonChoices.OTHER and not custom_reason:
        messages.error(request, "Please provide your specific reason when choosing 'Other'.")
        return redirect("marketplace:order_detail", order_number=order_number)

    RefundRequest.objects.create(
        order=order,
        user=request.user,
        amount=order.total_amount,
        reason=reason,
        custom_reason=custom_reason,
        additional_description=additional_desc,
        status=RefundRequest.StatusChoices.PENDING,
    )
    order.order_status = Order.REFUND_REQUESTED
    order.refund_status = Order.REFUND_REQUESTED
    order.save(update_fields=["order_status", "refund_status"])

    messages.success(
        request,
        f"Refund request submitted for Order #{order.order_number}. Our Admin team will review your request shortly."
    )
    return redirect("marketplace:order_detail", order_number=order_number)
