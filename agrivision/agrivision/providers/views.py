"""
Provider views — all protected by authentication and approval checks.

Access levels:
  - Any authenticated user:  apply, status
  - Approved Provider only:  dashboard, profile_edit, product_*, stock_*, orders
"""
from __future__ import annotations

from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from django.urls import reverse_lazy

from agrivision.marketplace.models import Category
from agrivision.marketplace.models import Order
from agrivision.marketplace.models import OrderItem
from agrivision.marketplace.models import Product
from agrivision.marketplace.models import StockHistory

from .forms import ProviderApplyForm
from .forms import ProviderProfileForm
from .forms import ProviderRequestForm
from .models import ProviderProfile, ProviderRequest, ProviderProduct


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / decorators
# ─────────────────────────────────────────────────────────────────────────────

def _get_provider_profile_or_none(user):
    """Return the user's ProviderProfile or None (never auto-creates)."""
    try:
        return user.provider_profile
    except ProviderProfile.DoesNotExist:
        return None


def approved_provider_required(view_func):
    """
    Decorator that ensures the user is:
      1. Logged in
      2. Has a ProviderProfile
      3. That profile is APPROVED
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse_lazy('users:login')}?next={request.path}")
        profile = _get_provider_profile_or_none(request.user)
        if profile is None or not profile.is_approved:
            return redirect("providers:status")
        return view_func(request, *args, **kwargs)
    return _wrapped


# ─────────────────────────────────────────────────────────────────────────────
# Apply to become a Provider
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def provider_apply(request):
    """Any logged-in user can apply to become a Provider."""
    profile = _get_provider_profile_or_none(request.user)

    if profile is not None:
        return redirect("providers:status")

    if request.method == "POST":
        form = ProviderApplyForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.verification_status = ProviderProfile.VerificationStatus.PENDING
            full_name = form.cleaned_data.get("full_name")
            if full_name:
                request.user.name = full_name
                request.user.save(update_fields=["name"])
            profile.save()
            messages.success(
                request,
                "✅ Your Provider application has been submitted! An admin will review it shortly.",
            )
            return redirect("providers:status")
    else:
        form = ProviderApplyForm()

    return render(request, "providers/apply.html", {"form": form})


# ─────────────────────────────────────────────────────────────────────────────
# Status page (pending / rejected)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def provider_status(request):
    profile = _get_provider_profile_or_none(request.user)

    if profile is None:
        return redirect("providers:apply")

    if profile.is_approved:
        return redirect("providers:dashboard")

    return render(request, "providers/status.html", {"profile": profile})


# ─────────────────────────────────────────────────────────────────────────────
# Provider Dashboard (approved only)
# ─────────────────────────────────────────────────────────────────────────────

@approved_provider_required
def provider_dashboard(request):
    """Main dashboard for approved providers."""
    profile = request.user.provider_profile

    # Products owned by this provider
    my_products = Product.objects.filter(
        provider=profile, is_active=True
    ).select_related("category").order_by("-created_at")

    # OrderItems for this provider's products
    my_order_items = (
        OrderItem.objects.filter(product__provider=profile)
        .select_related("order", "order__user", "product")
        .order_by("-order__created_at")
    )

    # Unique orders
    seen_order_ids = set()
    recent_orders = []
    for item in my_order_items[:50]:
        if item.order_id not in seen_order_ids:
            seen_order_ids.add(item.order_id)
            recent_orders.append(item.order)
            if len(recent_orders) >= 5:
                break

    # Stats
    total_stock = sum(p.stock for p in my_products)
    low_stock_count = my_products.filter(stock__gt=0, stock__lte=10).count()
    out_of_stock_count = my_products.filter(stock=0).count()
    total_orders_count = my_order_items.values("order").distinct().count()
    pending_orders_count = (
        my_order_items.filter(order__order_status="pending")
        .values("order")
        .distinct()
        .count()
    )
    completed_orders_count = (
        my_order_items.filter(order__order_status="delivered")
        .values("order")
        .distinct()
        .count()
    )
    total_revenue = sum(
        item.subtotal for item in my_order_items.filter(order__payment_status__in=["paid", "partially_paid"])
    )

    context = {
        "profile": profile,
        "my_products": my_products,
        "recent_orders": recent_orders,
        "total_stock": total_stock,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
        "total_orders_count": total_orders_count,
        "pending_orders_count": pending_orders_count,
        "completed_orders_count": completed_orders_count,
        "total_revenue": total_revenue,
        "products_count": my_products.count(),
    }
    return render(request, "providers/dashboard.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Provider Profile Edit (approved only)
# ─────────────────────────────────────────────────────────────────────────────

@approved_provider_required
def provider_profile_edit(request):
    """Approved provider can update their own farm/business details."""
    profile = request.user.provider_profile

    if request.method == "POST":
        form = ProviderProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Profile updated successfully.")
            return redirect("providers:dashboard")
    else:
        form = ProviderProfileForm(instance=profile)

    return render(request, "providers/profile_form.html", {"form": form, "profile": profile})


# ─────────────────────────────────────────────────────────────────────────────
# Provider Product Management (approved only)
# ─────────────────────────────────────────────────────────────────────────────

@approved_provider_required
def provider_product_list(request):
    """List all products owned by this provider."""
    profile = request.user.provider_profile
    products = Product.objects.filter(provider=profile).select_related("category").order_by("-created_at")

    context = {
        "profile": profile,
        "products": products,
    }
    return render(request, "providers/product_list.html", context)


def _ensure_default_categories():
    Category.objects.get_or_create(name="Seeds", defaults={"category_type": Category.SEEDS, "description": "Seeds for agriculture"})
    Category.objects.get_or_create(name="Plants", defaults={"category_type": Category.PLANTS, "description": "Plants and saplings"})


@approved_provider_required
def provider_product_add(request):
    """Approved provider registers a new seed/plant product."""
    _ensure_default_categories()
    profile = request.user.provider_profile

    if request.method == "POST":
        form = ProviderRequestForm(request.POST, request.FILES)
        if form.is_valid():
            item_name = form.cleaned_data["item_name"]
            category = form.cleaned_data["category"]
            description = form.cleaned_data.get("description", "")
            quantity = form.cleaned_data.get("quantity", 10)
            expected_price = form.cleaned_data.get("expected_price", 0.00)
            image = form.cleaned_data.get("image")
            image_url = form.cleaned_data.get("image_url")

            with transaction.atomic():
                product = Product.objects.create(
                    name=item_name,
                    category=category,
                    provider=profile,
                    provider_name=profile.farm_name,
                    provider_user=request.user,
                    description=description,
                    cost_price=expected_price,
                    price=expected_price,
                    stock=quantity,
                    image=image,
                    image_url=image_url,
                    is_active=True,
                )

                # Record Initial Stock History
                StockHistory.objects.create(
                    product=product,
                    provider=profile,
                    previous_stock=0,
                    quantity_changed=quantity,
                    new_stock=quantity,
                    change_type=StockHistory.ChangeType.INITIAL,
                    reason="Initial stock added during product registration",
                    created_by=request.user,
                )

                # Create mapping logs
                req = form.save(commit=False)
                req.provider = profile
                req.status = ProviderRequest.Status.APPROVED
                req.selling_price = expected_price
                req.admin_notes = "Auto-approved upon registration by provider."
                req.reviewed_by = request.user
                req.reviewed_at = timezone.now()
                req.created_product = product
                req.save()

                ProviderProduct.objects.create(
                    provider=profile,
                    product=product,
                    supplied_quantity=quantity,
                    unit_procurement_cost=expected_price,
                )

            messages.success(
                request,
                f"✅ '{product.name}' registered successfully! It is now live in the Marketplace with {product.stock} units.",
            )
            return redirect("providers:product_list")
    else:
        form = ProviderRequestForm()

    return render(request, "providers/product_form.html", {"form": form, "profile": profile, "is_edit": False})


@approved_provider_required
def provider_product_edit(request, pk):
    """Edit a marketplace product that belongs to this provider."""
    profile = request.user.provider_profile
    product = get_object_or_404(Product, pk=pk, provider=profile)

    from django import forms as django_forms

    class ProductEditForm(django_forms.ModelForm):
        class Meta:
            model = Product
            fields = ["name", "description", "price", "stock", "image", "is_active"]
            widgets = {
                "name": django_forms.TextInput(attrs={"class": "form-control"}),
                "description": django_forms.Textarea(attrs={"class": "form-control", "rows": 5, "placeholder": "Enter detailed plant description, care instructions, soil, sunlight, and watering guidance..."}),
                "price": django_forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
                "stock": django_forms.NumberInput(attrs={"class": "form-control", "min": 0}),
                "image": django_forms.ClearableFileInput(attrs={"class": "form-control"}),
                "is_active": django_forms.CheckboxInput(attrs={"class": "form-check-input"}),
            }

        def clean_price(self):
            price = self.cleaned_data.get("price")
            if price is not None and price <= 0:
                raise django_forms.ValidationError("Price must be greater than zero.")
            return price

        def clean_stock(self):
            stock = self.cleaned_data.get("stock")
            if stock is not None and stock < 0:
                raise django_forms.ValidationError("Stock cannot be negative.")
            return stock

        def clean(self):
            cleaned_data = super().clean()
            description = cleaned_data.get("description", "").strip()
            if not description:
                self.add_error("description", "Please provide a description and care details.")

            return cleaned_data

    if request.method == "POST":
        old_stock = product.stock
        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            with transaction.atomic():
                updated_prod = form.save()
                if updated_prod.stock != old_stock:
                    diff = updated_prod.stock - old_stock
                    StockHistory.objects.create(
                        product=updated_prod,
                        provider=profile,
                        previous_stock=old_stock,
                        quantity_changed=diff,
                        new_stock=updated_prod.stock,
                        change_type=StockHistory.ChangeType.MANUAL,
                        reason=f"Stock updated via product edit ({'+' if diff > 0 else ''}{diff})",
                        created_by=request.user,
                    )

            messages.success(request, f"✅ '{product.name}' updated successfully.")
            return redirect("providers:product_list")
    else:
        form = ProductEditForm(instance=product)

    return render(
        request,
        "providers/product_form.html",
        {"form": form, "profile": profile, "product": product, "is_edit": True},
    )


@approved_provider_required
def provider_product_delete(request, pk):
    profile = request.user.provider_profile
    product = get_object_or_404(Product, pk=pk, provider=profile)

    if request.method == "POST":
        product_name = product.name
        product.is_active = False
        product.save(update_fields=["is_active"])
        messages.success(request, f"🗑️ '{product_name}' has been deactivated.")
        return redirect("providers:product_list")

    return render(
        request,
        "providers/product_confirm_delete.html",
        {"product": product, "profile": profile},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Provider Stock Management & History
# ─────────────────────────────────────────────────────────────────────────────

@approved_provider_required
def provider_stock_management(request):
    profile = request.user.provider_profile
    products = Product.objects.filter(provider=profile).select_related("category").order_by("stock", "name")

    filter_type = request.GET.get("filter")
    if filter_type == "low":
        products = products.filter(stock__gt=0, stock__lte=10)
    elif filter_type == "out":
        products = products.filter(stock=0)
    elif filter_type == "healthy":
        products = products.filter(stock__gt=10)

    total_stock = sum(p.stock for p in products)
    low_count = Product.objects.filter(provider=profile, stock__gt=0, stock__lte=10).count()
    out_count = Product.objects.filter(provider=profile, stock=0).count()

    context = {
        "profile": profile,
        "products": products,
        "total_stock": total_stock,
        "low_count": low_count,
        "out_count": out_count,
        "filter_type": filter_type,
    }
    return render(request, "providers/stock_management.html", context)


@approved_provider_required
def provider_stock_adjust(request, pk):
    profile = request.user.provider_profile
    product = get_object_or_404(Product, pk=pk, provider=profile)

    if request.method == "POST":
        adj_type = request.POST.get("adjustment_type", "add")
        reason = request.POST.get("reason", "Manual stock adjustment by provider").strip()
        try:
            qty = int(request.POST.get("quantity", 0))
            if qty < 0:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(request, "Please enter a valid positive integer for quantity.")
            return redirect("providers:stock_management")

        old_stock = product.stock
        if adj_type == "add":
            new_stock = old_stock + qty
            change_type = StockHistory.ChangeType.ADDED
        elif adj_type == "subtract":
            new_stock = max(0, old_stock - qty)
            change_type = StockHistory.ChangeType.REMOVED
        else:  # set
            new_stock = qty
            change_type = StockHistory.ChangeType.MANUAL

        diff = new_stock - old_stock

        with transaction.atomic():
            product.stock = new_stock
            product.save(update_fields=["stock"])

            StockHistory.objects.create(
                product=product,
                provider=profile,
                previous_stock=old_stock,
                quantity_changed=diff,
                new_stock=new_stock,
                change_type=change_type,
                reason=reason,
                created_by=request.user,
            )

        messages.success(
            request,
            f"✅ Stock for '{product.name}' updated from {old_stock} to {new_stock} units ({'+' if diff > 0 else ''}{diff}).",
        )
    return redirect("providers:stock_management")


@approved_provider_required
def provider_stock_history(request):
    profile = request.user.provider_profile
    history_records = (
        StockHistory.objects.filter(provider=profile)
        .select_related("product", "related_order", "created_by")
        .order_by("-created_at")
    )

    product_filter = request.GET.get("product")
    if product_filter:
        history_records = history_records.filter(product_id=product_filter)

    my_products = Product.objects.filter(provider=profile).order_by("name")

    context = {
        "profile": profile,
        "history_records": history_records,
        "my_products": my_products,
        "selected_product": product_filter,
    }
    return render(request, "providers/stock_history.html", context)


# ─────────────────────────────────────────────────────────────────────────────
# Provider Orders (Isolated per provider)
# ─────────────────────────────────────────────────────────────────────────────

def _get_provider_next_action(order_status):
    """Return next sequential action for provider fulfillment workflow."""
    if order_status == Order.ORDER_PENDING:
        return {
            "target_status": Order.CONFIRMED,
            "label": "Confirm Order",
            "btn_class": "btn-primary",
            "icon": "bi-check2-circle",
            "tooltip": "Accept and confirm this incoming order",
        }
    elif order_status == Order.CONFIRMED:
        return {
            "target_status": Order.PROCESSING,
            "label": "Start Packing",
            "btn_class": "btn-info text-dark",
            "icon": "bi-box-seam",
            "tooltip": "Mark items as being packed and prepared in nursery",
        }
    elif order_status == Order.PROCESSING:
        return {
            "target_status": Order.SHIPPED,
            "label": "Dispatch / In Transit",
            "btn_class": "btn-warning text-dark",
            "icon": "bi-truck",
            "tooltip": "Hand over package to courier for transit to customer",
        }
    elif order_status == Order.SHIPPED:
        return {
            "target_status": Order.DELIVERED,
            "label": "Mark Delivered",
            "btn_class": "btn-success",
            "icon": "bi-house-check",
            "tooltip": "Complete doorstep delivery and settle COD balance",
        }
    return None


def _get_order_stage_info(order):
    """Return progress and metadata for the current order status."""
    status_progression = {
        Order.ORDER_PENDING: {
            "step": 1,
            "percent": 20,
            "label": "Order Placed & Awaiting Confirmation",
            "badge_class": "bg-warning text-dark",
            "icon": "bi-bag-check",
            "desc": "Order received from customer. Awaiting your nursery review and confirmation.",
        },
        Order.CONFIRMED: {
            "step": 2,
            "percent": 40,
            "label": "Confirmed by Provider",
            "badge_class": "bg-info text-dark",
            "icon": "bi-check2-circle",
            "desc": "Provider accepted fulfillment. Preparing nursery inventory.",
        },
        Order.PROCESSING: {
            "step": 3,
            "percent": 65,
            "label": "Packing & Quality Prep",
            "badge_class": "bg-primary",
            "icon": "bi-box-seam",
            "desc": "Seeds/plants are being packed in secure agricultural packaging.",
        },
        Order.SHIPPED: {
            "step": 4,
            "percent": 85,
            "label": "Out for Delivery / In Transit",
            "badge_class": "bg-primary",
            "icon": "bi-truck",
            "desc": "Package is in transit via courier to customer destination.",
        },
        Order.DELIVERED: {
            "step": 5,
            "percent": 100,
            "label": "Delivered & Balance Settled",
            "badge_class": "bg-success",
            "icon": "bi-house-check",
            "desc": "Order delivered to doorstep. Cash on Delivery balance settled.",
        },
        Order.CANCELLED: {
            "step": 0,
            "percent": 0,
            "label": "Cancelled",
            "badge_class": "bg-danger",
            "icon": "bi-x-circle",
            "desc": f"Order cancelled. Reason: {order.cancellation_reason or 'No reason provided.'}",
        },
        Order.REFUND_REQUESTED: {
            "step": 0,
            "percent": 0,
            "label": "Refund Requested",
            "badge_class": "bg-warning text-dark",
            "icon": "bi-arrow-counterclockwise",
            "desc": "Customer requested a return/refund. Admin review in progress.",
        },
        Order.REFUNDED: {
            "step": 0,
            "percent": 0,
            "label": "Refunded",
            "badge_class": "bg-secondary",
            "icon": "bi-check2-all",
            "desc": "Refund approved and completed.",
        },
    }
    return status_progression.get(order.order_status, {
        "step": 1,
        "percent": 20,
        "label": order.get_order_status_display(),
        "badge_class": "bg-secondary",
        "icon": "bi-info-circle",
        "desc": "",
    })


@approved_provider_required
def provider_orders(request):
    profile = request.user.provider_profile

    # Fetch all OrderItems belonging to this provider
    my_order_items = (
        OrderItem.objects.filter(
            Q(provider=profile) | Q(product__provider=profile) | Q(provider_user=request.user)
        )
        .select_related("order", "order__user", "product", "product__category")
        .order_by("-order__created_at")
    )

    # Group items by order
    orders_map: dict = {}
    for item in my_order_items:
        oid = item.order_id
        if oid not in orders_map:
            orders_map[oid] = {
                "order": item.order,
                "items": [],
                "subtotal": Decimal("0.00"),
            }
        orders_map[oid]["items"].append(item)
        orders_map[oid]["subtotal"] += (item.subtotal or Decimal("0.00"))

    all_orders = list(orders_map.values())

    # Calculate status counts for filtering pills
    counts = {
        "all": len(all_orders),
        "pending": sum(1 for e in all_orders if e["order"].order_status == Order.ORDER_PENDING),
        "confirmed": sum(1 for e in all_orders if e["order"].order_status == Order.CONFIRMED),
        "processing": sum(1 for e in all_orders if e["order"].order_status == Order.PROCESSING),
        "shipped": sum(1 for e in all_orders if e["order"].order_status == Order.SHIPPED),
        "delivered": sum(1 for e in all_orders if e["order"].order_status == Order.DELIVERED),
        "cancelled": sum(1 for e in all_orders if e["order"].order_status == Order.CANCELLED),
    }

    # Filters
    selected_status = request.GET.get("status", "all").strip().lower()
    selected_payment = request.GET.get("payment_method", "all").strip().lower()
    query = request.GET.get("q", "").strip()

    filtered_orders = all_orders

    if selected_status in ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]:
        filtered_orders = [e for e in filtered_orders if e["order"].order_status == selected_status]

    if selected_payment in [Order.ONLINE, Order.HALF_COD, Order.COD]:
        filtered_orders = [e for e in filtered_orders if e["order"].payment_method == selected_payment]

    if query:
        q_lower = query.lower()
        filtered_orders = [
            e for e in filtered_orders
            if q_lower in e["order"].order_number.lower()
            or q_lower in e["order"].full_name.lower()
            or q_lower in e["order"].phone.lower()
            or q_lower in e["order"].city.lower()
            or q_lower in e["order"].district.lower()
            or any(q_lower in item.product_name.lower() for item in e["items"])
        ]

    # Attach next actions, stage info, and refund claims
    for entry in filtered_orders:
        order = entry["order"]
        entry["next_action"] = _get_provider_next_action(order.order_status)
        entry["stage_info"] = _get_order_stage_info(order)
        entry["refund_requests"] = list(order.refund_requests.all().order_by("-created_at"))

    context = {
        "profile": profile,
        "provider_orders": filtered_orders,
        "total_orders": len(filtered_orders),
        "all_count": len(all_orders),
        "counts": counts,
        "selected_status": selected_status,
        "selected_payment": selected_payment,
        "query": query,
        "order_status_choices": Order.ORDER_STATUS_CHOICES,
        "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, "providers/orders.html", context)


@approved_provider_required
def provider_order_detail(request, order_id):
    """Detailed view for provider to inspect items, customer address, and update status."""
    profile = request.user.provider_profile
    order = get_object_or_404(Order, id=order_id)

    order_items = (
        OrderItem.objects.filter(
            Q(provider=profile) | Q(product__provider=profile) | Q(provider_user=request.user),
            order=order,
        )
        .select_related("product", "product__category")
    )

    if not order_items.exists():
        messages.error(request, "You do not have permission to view this order.")
        return redirect("providers:orders")

    subtotal = sum((item.subtotal or Decimal("0.00")) for item in order_items)
    next_action = _get_provider_next_action(order.order_status)
    stage_info = _get_order_stage_info(order)
    refund_requests = order.refund_requests.all().order_by("-created_at")

    context = {
        "profile": profile,
        "order": order,
        "order_items": order_items,
        "subtotal": subtotal,
        "next_action": next_action,
        "stage_info": stage_info,
        "refund_requests": refund_requests,
        "order_status_choices": Order.ORDER_STATUS_CHOICES,
        "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,
    }
    return render(request, "providers/order_detail.html", context)


@approved_provider_required
def provider_order_status_update(request, order_id):
    if request.method != "POST":
        return redirect("providers:orders")

    profile = request.user.provider_profile
    has_product = OrderItem.objects.filter(
        Q(provider=profile) | Q(product__provider=profile) | Q(provider_user=request.user),
        order_id=order_id,
    ).exists()

    if not has_product:
        messages.error(request, "You do not have permission to update this order.")
        return redirect("providers:orders")

    order = get_object_or_404(Order, id=order_id)
    new_order_status = request.POST.get("order_status")
    new_payment_status = request.POST.get("payment_status")
    cancellation_reason = request.POST.get("cancellation_reason", "").strip()

    valid_order_statuses = dict(Order.ORDER_STATUS_CHOICES)
    valid_payment_statuses = dict(Order.PAYMENT_STATUS_CHOICES)

    updated = False
    old_status = order.order_status

    if new_order_status in valid_order_statuses and new_order_status != old_status:
        # Handle Cancellation
        if new_order_status == Order.CANCELLED and old_status != Order.CANCELLED:
            order.order_status = Order.CANCELLED
            order.cancelled_at = timezone.now()
            order.cancellation_reason = cancellation_reason or f"Cancelled by provider {profile.farm_name}."

            # Restore stock for provider's items
            order_items = OrderItem.objects.filter(
                Q(provider=profile) | Q(product__provider=profile) | Q(provider_user=request.user),
                order=order,
            ).select_related("product")

            for item in order_items:
                if item.product:
                    prev_stock = item.product.stock
                    item.product.stock += item.quantity
                    item.product.save(update_fields=["stock"])
                    StockHistory.objects.create(
                        product=item.product,
                        provider=profile,
                        previous_stock=prev_stock,
                        quantity_changed=item.quantity,
                        new_stock=item.product.stock,
                        change_type=StockHistory.ChangeType.CANCELLATION,
                        reason=f"Order #{order.order_number} cancelled by provider",
                        related_order=order,
                        created_by=request.user,
                    )
            updated = True
        else:
            order.order_status = new_order_status

            # When provider confirms or starts processing the order:
            if new_order_status in [Order.CONFIRMED, Order.PROCESSING]:
                # Advance payment activates upon provider acceptance
                if order.payment_method == Order.HALF_COD and order.payment_status == Order.PENDING:
                    order.payment_status = Order.PARTIALLY_PAID
                    if getattr(order, "payment_record", None):
                        order.payment_record.status = Order.PARTIALLY_PAID
                        order.payment_record.save()
                elif order.payment_method == Order.ONLINE and order.payment_status == Order.PENDING:
                    order.payment_status = Order.PAID
                    if getattr(order, "payment_record", None):
                        order.payment_record.status = Order.PAID
                        order.payment_record.save()

            # If delivered, auto-settle the remaining Cash on Delivery balance
            elif new_order_status == Order.DELIVERED and order.payment_status in [
                Order.PARTIALLY_PAID,
                Order.PENDING,
                Order.COD_PENDING,
            ]:
                order.payment_status = Order.PAID
                if getattr(order, "payment_record", None):
                    order.payment_record.status = Order.PAID
                    order.payment_record.save()
            updated = True

    if new_payment_status in valid_payment_statuses:
        order.payment_status = new_payment_status
        if getattr(order, "payment_record", None):
            order.payment_record.status = new_payment_status
            order.payment_record.save()
        updated = True

    if updated:
        order.save()
        messages.success(
            request,
            f"✅ Order #{order.order_number} status updated to '{order.get_order_status_display()}'.",
        )

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect("providers:orders")


@approved_provider_required
def provider_orders_view(request):
    """View-only summary of orders for quick analytics."""
    return provider_orders(request)

