"""
Provider views — all protected by authentication and approval checks.

Access levels:
  - Any authenticated user:  apply, status
  - Approved Provider only:  dashboard, profile_edit, product_*, orders
"""
from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic import ListView
from django.urls import reverse_lazy

from agrivision.marketplace.models import Category
from agrivision.marketplace.models import Order
from agrivision.marketplace.models import OrderItem
from agrivision.marketplace.models import Product

from .forms import ProviderApplyForm
from .forms import ProviderProfileForm
from .forms import ProviderRequestForm
from .models import ProviderProfile
from .models import ProviderRequest


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

    Redirects otherwise:
      - Not logged in          → login page
      - No profile / PENDING   → providers:status
      - REJECTED               → providers:status
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
    """
    Any logged-in user can apply to become a Provider.
    If they already have a profile (pending/approved/rejected), redirect to status.
    """
    profile = _get_provider_profile_or_none(request.user)

    if profile is not None:
        # Already applied — show current status
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
                "✅ Your Provider application has been submitted! "
                "An admin will review it shortly.",
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
    """
    Show the current provider application status.
    Approved providers are redirected to the dashboard.
    Users with no profile are redirected to apply.
    """
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

    # Products owned by this provider (marketplace.Product)
    my_products = Product.objects.filter(
        provider=profile, is_active=True
    ).select_related("category").order_by("-created_at")

    # Orders that contain any of this provider's products
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

    # Product submissions (ProviderRequests) pending admin review
    pending_requests = profile.product_requests.filter(
        status=ProviderRequest.Status.PENDING
    ).order_by("-created_at")

    # Stats
    total_stock = sum(p.stock for p in my_products)
    total_orders_count = my_order_items.values("order").distinct().count()
    pending_orders_count = (
        my_order_items.filter(order__order_status="pending")
        .values("order")
        .distinct()
        .count()
    )

    context = {
        "profile": profile,
        "my_products": my_products,
        "recent_orders": recent_orders,
        "pending_requests": pending_requests,
        "total_stock": total_stock,
        "total_orders_count": total_orders_count,
        "pending_orders_count": pending_orders_count,
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
    # Also show pending requests
    pending_requests = profile.product_requests.filter(
        status=ProviderRequest.Status.PENDING
    ).order_by("-created_at")

    context = {
        "profile": profile,
        "products": products,
        "pending_requests": pending_requests,
    }
    return render(request, "providers/product_list.html", context)


@approved_provider_required
def provider_product_add(request):
    """
    Approved provider submits a new product request for Admin review.
    The admin then creates the marketplace.Product and links it back.
    """
    profile = request.user.provider_profile

    if request.method == "POST":
        form = ProviderRequestForm(request.POST, request.FILES)
        if form.is_valid():
            req = form.save(commit=False)
            req.provider = profile
            req.status = ProviderRequest.Status.PENDING
            req.save()
            messages.success(
                request,
                f"✅ '{req.item_name}' submitted for Admin review. "
                "It will appear in the marketplace once approved.",
            )
            return redirect("providers:product_list")
    else:
        form = ProviderRequestForm()

    return render(request, "providers/product_form.html", {"form": form, "profile": profile, "is_edit": False})


@approved_provider_required
def provider_product_edit(request, pk):
    """Edit a marketplace product that belongs to this provider."""
    profile = request.user.provider_profile
    # Ownership check — provider can only edit THEIR OWN products
    product = get_object_or_404(Product, pk=pk, provider=profile)

    # Build a simple edit form from the Product model directly
    from django import forms as django_forms

    class ProductEditForm(django_forms.ModelForm):
        class Meta:
            model = Product
            fields = ["name", "category", "description", "price", "stock", "image", "is_active"]
            widgets = {
                "name": django_forms.TextInput(attrs={"class": "form-control"}),
                "category": django_forms.Select(attrs={"class": "form-select"}),
                "description": django_forms.Textarea(attrs={"class": "form-control", "rows": 3}),
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

    if request.method == "POST":
        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
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
    """Delete (deactivate) a marketplace product owned by this provider."""
    profile = request.user.provider_profile
    product = get_object_or_404(Product, pk=pk, provider=profile)

    if request.method == "POST":
        product_name = product.name
        # Soft-delete: deactivate rather than hard-delete (preserves order history)
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
# Provider Orders (approved only)
# ─────────────────────────────────────────────────────────────────────────────

@approved_provider_required
def provider_orders(request):
    """
    Show orders that contain at least one product belonging to this provider.
    Provider A cannot see orders for Provider B's products.
    """
    profile = request.user.provider_profile

    # Get all OrderItems for this provider's products
    my_order_items = (
        OrderItem.objects.filter(product__provider=profile)
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
                "subtotal": 0,
            }
        orders_map[oid]["items"].append(item)
        orders_map[oid]["subtotal"] += item.subtotal

    provider_orders_list = list(orders_map.values())

    context = {
        "profile": profile,
        "provider_orders": provider_orders_list,
        "total_orders": len(provider_orders_list),
    }
    return render(request, "providers/orders.html", context)
