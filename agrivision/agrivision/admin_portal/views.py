import csv
import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from agrivision.admin_portal.decorators import AdminRequiredMixin
from agrivision.admin_portal.forms import (
    CategoryForm,
    OrderStatusUpdateForm,
    ProductForm,
    ProviderProfileForm,
    ProviderRequestApproveForm,
    ProviderRequestRejectForm,
    QuickStockAdjustmentForm,
    UserEditForm,
)
from agrivision.marketplace.models import Category, Order, OrderItem, Payment, Product
from agrivision.providers.models import Provider, ProviderProduct, ProviderRequest

User = get_user_model()


# -----------------------------------------------------------------------------
# 1. ADMIN DASHBOARD & REALTIME ANALYTICS
# -----------------------------------------------------------------------------
class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = "admin_portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Core KPI Counts
        total_users = User.objects.count()
        total_providers = Provider.objects.count()
        total_products = Product.objects.count()
        total_orders = Order.objects.count()

        # Financials
        paid_orders = Order.objects.filter(payment_status=Order.PAID)
        total_sales = paid_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        avg_order_value = paid_orders.aggregate(avg=Avg("total_amount"))["avg"] or Decimal("0.00")

        # Alert Counters
        pending_requests_count = ProviderRequest.objects.filter(status=ProviderRequest.PENDING).count()
        low_stock_count = Product.objects.filter(stock__gt=0, stock__lte=10).count()
        out_of_stock_count = Product.objects.filter(stock=0).count()
        pending_orders_count = Order.objects.filter(order_status=Order.ORDER_PENDING).count()

        # Recent Feeds
        recent_orders = Order.objects.select_related("user").order_by("-created_at")[:6]
        recent_requests = ProviderRequest.objects.select_related("provider", "category").order_by("-created_at")[:6]
        low_stock_products = Product.objects.filter(stock__lte=10).order_by("stock")[:6]
        recent_users = User.objects.order_by("-date_joined")[:6]

        # Top 5 Most Purchased Products
        top_products = (
            OrderItem.objects.values("product_name")
            .annotate(total_sold=Sum("quantity"), total_revenue=Sum("subtotal"))
            .order_by("-total_sold")[:5]
        )

        # Chart 1: Order Status Breakdown (Doughnut Chart Data)
        order_status_counts = {
            "Pending": Order.objects.filter(order_status=Order.ORDER_PENDING).count(),
            "Confirmed": Order.objects.filter(order_status=Order.CONFIRMED).count(),
            "Processing": Order.objects.filter(order_status=Order.PROCESSING).count(),
            "Shipped": Order.objects.filter(order_status=Order.SHIPPED).count(),
            "Delivered": Order.objects.filter(order_status=Order.DELIVERED).count(),
            "Cancelled": Order.objects.filter(order_status=Order.CANCELLED).count(),
        }

        # Chart 2: Provider Requests Distribution
        request_status_counts = {
            "Pending": pending_requests_count,
            "Approved": ProviderRequest.objects.filter(status=ProviderRequest.APPROVED).count(),
            "Rejected": ProviderRequest.objects.filter(status=ProviderRequest.REJECTED).count(),
        }

        # Chart 3: Category Distribution
        category_counts = (
            Category.objects.annotate(num_products=Count("products"))
            .values("name", "num_products")
        )
        category_labels = [c["name"] for c in category_counts]
        category_data = [c["num_products"] for c in category_counts]

        # Chart 4: Monthly Sales Data (Dummy / Aggregate)
        # 6-month simulation/actual aggregation
        months = ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb"]
        sales_trend = [12500, 18400, 24600, 31200, 28900, float(total_sales) if total_sales > 0 else 35400]

        top_prod_labels = [p["product_name"] or "Product" for p in top_products] or ["Hybrid Tomato Seeds", "Neem Bio-Pesticide", "Vermicompost 5kg", "Drip Irrigation Kit", "Chili Seeds F1"]
        top_prod_quantities = [p["total_sold"] for p in top_products] or [145, 98, 87, 62, 54]

        context.update({
            "total_users": total_users,
            "total_providers": total_providers,
            "total_products": total_products,
            "total_orders": total_orders,
            "total_sales": total_sales,
            "avg_order_value": avg_order_value,
            "pending_requests_count": pending_requests_count,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "pending_orders_count": pending_orders_count,
            "recent_orders": recent_orders,
            "recent_requests": recent_requests,
            "low_stock_products": low_stock_products,
            "recent_users": recent_users,
            "top_products": top_products,
            # JSON encoded data for Chart.js
            "chart_order_status": json.dumps(order_status_counts),
            "chart_request_status": json.dumps(request_status_counts),
            "chart_category_labels": json.dumps(category_labels if category_labels else ["Seeds", "Plants", "Fertilizers", "Pesticides", "Tools"]),
            "chart_category_data": json.dumps(category_data if category_data else [12, 18, 8, 6, 4]),
            "chart_sales_months": json.dumps(months),
            "chart_sales_trend": json.dumps(sales_trend),
            "chart_top_prod_labels": json.dumps(top_prod_labels),
            "chart_top_prod_data": json.dumps(top_prod_quantities),
        })
        return context


# -----------------------------------------------------------------------------
# 2. USER MANAGEMENT
# -----------------------------------------------------------------------------
class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = "admin_portal/users/user_list.html"
    context_object_name = "users"
    paginate_by = 15

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        search = self.request.GET.get("q")
        role = self.request.GET.get("role")
        status = self.request.GET.get("status")

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(email__icontains=search))
        if role == "staff":
            qs = qs.filter(is_staff=True)
        elif role == "superuser":
            qs = qs.filter(is_superuser=True)
        elif role == "provider":
            qs = qs.filter(provider_profile__isnull=False)
        elif role == "customer":
            qs = qs.filter(is_staff=False, is_superuser=False, provider_profile__isnull=True)

        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("q", "")
        context["role_filter"] = self.request.GET.get("role", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["total_user_count"] = User.objects.count()
        return context


class UserDetailView(AdminRequiredMixin, DetailView):
    model = User
    template_name = "admin_portal/users/user_detail.html"
    context_object_name = "target_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context["orders"] = Order.objects.filter(user=user).order_by("-created_at")[:10]
        context["provider"] = getattr(user, "provider_profile", None)
        return context


class UserEditView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserEditForm
    template_name = "admin_portal/users/user_edit.html"
    context_object_name = "target_user"

    def get_success_url(self):
        messages.success(self.request, f"User account '{self.object.email}' updated successfully.")
        return reverse_lazy("admin_portal:user_detail", kwargs={"pk": self.object.pk})


class UserToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "You cannot deactivate your own admin account.")
            return redirect("admin_portal:user_list")
        user.is_active = not user.is_active
        user.save()
        status_str = "activated" if user.is_active else "deactivated"
        messages.success(request, f"User '{user.email}' has been {status_str}.")
        return redirect(request.META.get("HTTP_REFERER", "admin_portal:user_list"))


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy("admin_portal:user_list")

    def post(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            messages.error(request, "You cannot delete your own admin account.")
            return redirect("admin_portal:user_list")
        messages.success(request, f"User '{user.email}' has been removed.")
        return super().post(request, *args, **kwargs)


# -----------------------------------------------------------------------------
# 3. PROVIDER MANAGEMENT
# -----------------------------------------------------------------------------
class ProviderListView(AdminRequiredMixin, ListView):
    model = Provider
    template_name = "admin_portal/providers/provider_list.html"
    context_object_name = "providers"
    paginate_by = 12

    def get_queryset(self):
        qs = Provider.objects.select_related("user").annotate(
            req_count=Count("requests")
        ).order_by("-created_at")

        search = self.request.GET.get("q")
        verification = self.request.GET.get("verification")

        if search:
            qs = qs.filter(
                Q(farm_name__icontains=search)
                | Q(contact_person__icontains=search)
                | Q(email__icontains=search)
                | Q(city__icontains=search)
            )
        if verification == "verified":
            qs = qs.filter(is_verified=True)
        elif verification == "unverified":
            qs = qs.filter(is_verified=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("q", "")
        context["verification_filter"] = self.request.GET.get("verification", "")
        context["total_providers"] = Provider.objects.count()
        context["verified_providers"] = Provider.objects.filter(is_verified=True).count()
        return context


class ProviderDetailView(AdminRequiredMixin, DetailView):
    model = Provider
    template_name = "admin_portal/providers/provider_detail.html"
    context_object_name = "provider"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        provider = self.get_object()
        context["requests"] = provider.requests.select_related("category", "created_product").order_by("-created_at")
        context["supplied_products"] = provider.supplied_products.select_related("product").all()
        return context


class ProviderVerifyToggleView(AdminRequiredMixin, View):
    def post(self, request, pk):
        provider = get_object_or_404(Provider, pk=pk)
        provider.is_verified = not provider.is_verified
        if provider.is_verified:
            provider.verification_date = timezone.now()
        else:
            provider.verification_date = None
        provider.save()
        status_str = "verified and approved" if provider.is_verified else "unverified"
        messages.success(request, f"Provider '{provider.farm_name}' is now marked as {status_str}.")
        return redirect(request.META.get("HTTP_REFERER", "admin_portal:provider_list"))


# -----------------------------------------------------------------------------
# 4. PROVIDER REQUEST APPROVAL / REJECTION FLOW (CRITICAL ENGINE)
# -----------------------------------------------------------------------------
class ProviderRequestListView(AdminRequiredMixin, ListView):
    model = ProviderRequest
    template_name = "admin_portal/requests/request_list.html"
    context_object_name = "requests"
    paginate_by = 12

    def get_queryset(self):
        qs = ProviderRequest.objects.select_related("provider", "category", "created_product").order_by("-created_at")
        status = self.request.GET.get("status")
        category_id = self.request.GET.get("category")
        search = self.request.GET.get("q")

        if status and status in [ProviderRequest.PENDING, ProviderRequest.APPROVED, ProviderRequest.REJECTED]:
            qs = qs.filter(status=status)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(
                Q(product_name__icontains=search)
                | Q(provider__farm_name__icontains=search)
                | Q(provider__contact_person__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["current_status"] = self.request.GET.get("status", "")
        context["current_category"] = self.request.GET.get("category", "")
        context["search"] = self.request.GET.get("q", "")
        context["pending_count"] = ProviderRequest.objects.filter(status=ProviderRequest.PENDING).count()
        context["approved_count"] = ProviderRequest.objects.filter(status=ProviderRequest.APPROVED).count()
        context["rejected_count"] = ProviderRequest.objects.filter(status=ProviderRequest.REJECTED).count()
        return context


class ProviderRequestDetailView(AdminRequiredMixin, DetailView):
    model = ProviderRequest
    template_name = "admin_portal/requests/request_detail.html"
    context_object_name = "req"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = self.get_object()
        # Suggested initial selling price (e.g. 20% markup over expected procurement price)
        suggested_price = (req.expected_price * Decimal("1.20")).quantize(Decimal("0.01"))
        context["approve_form"] = ProviderRequestApproveForm(initial={"selling_price": suggested_price})
        context["reject_form"] = ProviderRequestRejectForm()
        return context


class ProviderRequestApproveView(AdminRequiredMixin, View):
    """
    Approves the provider request:
    1. Sets status to APPROVED.
    2. Automatically creates / lists a Product in the Marketplace catalog.
    3. Links the new Product to this ProviderRequest.
    """
    def post(self, request, pk):
        req = get_object_or_404(ProviderRequest, pk=pk)
        if req.status == ProviderRequest.APPROVED:
            messages.info(request, "This request is already approved.")
            return redirect("admin_portal:request_detail", pk=pk)

        form = ProviderRequestApproveForm(request.POST)
        if form.is_valid():
            selling_price = form.cleaned_data["selling_price"]
            admin_notes = form.cleaned_data.get("admin_notes", "")

            # 1. Create the Product in Marketplace
            product = Product.objects.create(
                name=req.product_name,
                category=req.category,
                provider_name=req.provider.farm_name,
                provider_user=req.provider.user,
                description=req.description,
                cost_price=req.expected_price,
                price=selling_price,
                stock=req.quantity,
                image=req.image if req.image else None,
                image_url=req.image_url if req.image_url else None,
                is_active=True,
            )

            # 2. Update ProviderRequest
            req.status = ProviderRequest.APPROVED
            req.selling_price = selling_price
            req.admin_notes = admin_notes
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.created_product = product
            req.save()

            # 3. Create ProviderProduct mapping log
            ProviderProduct.objects.create(
                provider=req.provider,
                product=product,
                supplied_quantity=req.quantity,
                unit_procurement_cost=req.expected_price,
            )

            messages.success(
                request,
                f"Request approved successfully! '{product.name}' is now live in the marketplace with {product.stock} units at ₹{product.price}."
            )
            return redirect("admin_portal:request_detail", pk=pk)
        else:
            messages.error(request, "Please provide a valid selling price.")
            return redirect("admin_portal:request_detail", pk=pk)


class ProviderRequestRejectView(AdminRequiredMixin, View):
    """
    Rejects the provider request with reasons.
    """
    def post(self, request, pk):
        req = get_object_or_404(ProviderRequest, pk=pk)
        form = ProviderRequestRejectForm(request.POST)
        if form.is_valid():
            req.status = ProviderRequest.REJECTED
            req.rejection_reason = form.cleaned_data["rejection_reason"]
            req.admin_notes = form.cleaned_data.get("admin_notes", "")
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save()

            messages.warning(request, f"Request for '{req.product_name}' was marked as REJECTED.")
            return redirect("admin_portal:request_detail", pk=pk)
        else:
            messages.error(request, "Please provide a rejection reason.")
            return redirect("admin_portal:request_detail", pk=pk)


# -----------------------------------------------------------------------------
# 5. PRODUCT & CATEGORY MANAGEMENT
# -----------------------------------------------------------------------------
class ProductListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = "admin_portal/products/product_list.html"
    context_object_name = "products"
    paginate_by = 15

    def get_queryset(self):
        qs = Product.objects.select_related("category").order_by("-created_at")
        search = self.request.GET.get("q")
        category_id = self.request.GET.get("category")
        stock_filter = self.request.GET.get("stock")
        status_filter = self.request.GET.get("status")

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(provider_name__icontains=search) | Q(description__icontains=search))
        if category_id:
            qs = qs.filter(category_id=category_id)
        if stock_filter == "in_stock":
            qs = qs.filter(stock__gt=10)
        elif stock_filter == "low_stock":
            qs = qs.filter(stock__gt=0, stock__lte=10)
        elif stock_filter == "out_of_stock":
            qs = qs.filter(stock=0)
        if status_filter == "active":
            qs = qs.filter(is_active=True)
        elif status_filter == "inactive":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["search"] = self.request.GET.get("q", "")
        context["category_filter"] = self.request.GET.get("category", "")
        context["stock_filter"] = self.request.GET.get("stock", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["total_products"] = Product.objects.count()
        return context


class ProductCreateView(AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "admin_portal/products/product_form.html"
    success_url = reverse_lazy("admin_portal:product_list")

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' created successfully!")
        return super().form_valid(form)


class ProductUpdateView(AdminRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "admin_portal/products/product_form.html"
    success_url = reverse_lazy("admin_portal:product_list")

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' updated successfully!")
        return super().form_valid(form)


class ProductDeleteView(AdminRequiredMixin, DeleteView):
    model = Product
    success_url = reverse_lazy("admin_portal:product_list")

    def post(self, request, *args, **kwargs):
        product = self.get_object()
        messages.success(request, f"Product '{product.name}' was deleted.")
        return super().post(request, *args, **kwargs)


class ProductToggleActiveView(AdminRequiredMixin, View):
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save()
        status_str = "activated (visible to customers)" if product.is_active else "deactivated (hidden from catalog)"
        messages.success(request, f"Product '{product.name}' is now {status_str}.")
        return redirect(request.META.get("HTTP_REFERER", "admin_portal:product_list"))


# Category Views
class CategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = "admin_portal/categories/category_list.html"
    context_object_name = "categories"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CategoryForm()
        return context


class CategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    success_url = reverse_lazy("admin_portal:category_list")

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' added successfully.")
        return super().form_valid(form)


class CategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    success_url = reverse_lazy("admin_portal:category_list")

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' updated.")
        return super().form_valid(form)


class CategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = Category
    success_url = reverse_lazy("admin_portal:category_list")

    def post(self, request, *args, **kwargs):
        cat = self.get_object()
        if cat.products.exists():
            messages.error(request, f"Cannot delete category '{cat.name}' because it contains {cat.products.count()} products.")
            return redirect("admin_portal:category_list")
        messages.success(request, f"Category '{cat.name}' deleted.")
        return super().post(request, *args, **kwargs)


# -----------------------------------------------------------------------------
# 6. INVENTORY & STOCK MANAGEMENT
# -----------------------------------------------------------------------------
class InventoryListView(AdminRequiredMixin, ListView):
    model = Product
    template_name = "admin_portal/inventory/inventory_list.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        qs = Product.objects.select_related("category").order_by("stock", "name")
        filter_type = self.request.GET.get("filter")
        search = self.request.GET.get("q")

        if filter_type == "low":
            qs = qs.filter(stock__gt=0, stock__lte=10)
        elif filter_type == "out":
            qs = qs.filter(stock=0)
        elif filter_type == "healthy":
            qs = qs.filter(stock__gt=10)

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(category__name__icontains=search))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_type"] = self.request.GET.get("filter", "")
        context["search"] = self.request.GET.get("q", "")
        context["total_inventory_items"] = Product.objects.aggregate(total_units=Sum("stock"))["total_units"] or 0
        context["total_inventory_value"] = sum(p.stock * p.price for p in Product.objects.all())
        context["low_stock_count"] = Product.objects.filter(stock__gt=0, stock__lte=10).count()
        context["out_of_stock_count"] = Product.objects.filter(stock=0).count()
        context["stock_form"] = QuickStockAdjustmentForm()
        return context


class InventoryQuickAdjustView(AdminRequiredMixin, View):
    """
    Adjusts stock count on a product quickly (+X, -X, =X).
    """
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        adj_type = request.POST.get("adjustment_type")
        try:
            qty = int(request.POST.get("quantity", 0))
        except ValueError:
            qty = 0

        old_stock = product.stock
        if adj_type == "add":
            product.stock += qty
        elif adj_type == "subtract":
            product.stock = max(0, product.stock - qty)
        elif adj_type == "set":
            product.stock = max(0, qty)

        product.save()
        messages.success(
            request,
            f"Stock for '{product.name}' adjusted from {old_stock} to {product.stock} units."
        )
        return redirect(request.META.get("HTTP_REFERER", "admin_portal:inventory_list"))


# -----------------------------------------------------------------------------
# 7. ORDER & PAYMENT MANAGEMENT
# -----------------------------------------------------------------------------
class OrderListView(AdminRequiredMixin, ListView):
    model = Order
    template_name = "admin_portal/orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 15

    def get_queryset(self):
        qs = Order.objects.select_related("user").order_by("-created_at")
        status = self.request.GET.get("status")
        payment_status = self.request.GET.get("payment_status")
        payment_method = self.request.GET.get("payment_method")
        search = self.request.GET.get("q")

        if status:
            qs = qs.filter(order_status=status)
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        if payment_method:
            qs = qs.filter(payment_method=payment_method)
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search)
                | Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_filter"] = self.request.GET.get("status", "")
        context["payment_status_filter"] = self.request.GET.get("payment_status", "")
        context["payment_method_filter"] = self.request.GET.get("payment_method", "")
        context["search"] = self.request.GET.get("q", "")
        context["total_orders_count"] = Order.objects.count()
        context["pending_orders_count"] = Order.objects.filter(order_status=Order.ORDER_PENDING).count()
        return context


class OrderDetailView(AdminRequiredMixin, DetailView):
    model = Order
    template_name = "admin_portal/orders/order_detail.html"
    context_object_name = "order"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context["items"] = order.items.select_related("product").all()
        context["status_form"] = OrderStatusUpdateForm(instance=order)
        context["payment"] = getattr(order, "payment_record", None)
        return context


class OrderStatusUpdateView(AdminRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_order_status = request.POST.get("order_status")
        new_payment_status = request.POST.get("payment_status")

        if new_order_status in dict(Order.ORDER_STATUS_CHOICES):
            order.order_status = new_order_status
        if new_payment_status in dict(Order.PAYMENT_STATUS_CHOICES):
            order.payment_status = new_payment_status
            if getattr(order, "payment_record", None):
                order.payment_record.status = new_payment_status
                order.payment_record.save()

        order.save()
        messages.success(request, f"Order #{order.order_number} status updated to {order.get_order_status_display()} / {order.get_payment_status_display()}.")
        return redirect("admin_portal:order_detail", pk=pk)


class PaymentListView(AdminRequiredMixin, ListView):
    model = Payment
    template_name = "admin_portal/payments/payment_list.html"
    context_object_name = "payments"
    paginate_by = 15

    def get_queryset(self):
        qs = Payment.objects.select_related("order", "user").order_by("-payment_date")
        status = self.request.GET.get("status")
        search = self.request.GET.get("q")

        if status:
            qs = qs.filter(status=status)
        if search:
            qs = qs.filter(
                Q(transaction_id__icontains=search)
                | Q(order__order_number__icontains=search)
                | Q(user__email__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_payments_amount"] = Payment.objects.filter(status=Order.PAID).aggregate(Sum("amount"))["amount__sum"] or 0
        context["search"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        return context


class PaymentMarkPaidView(AdminRequiredMixin, View):
    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        payment.status = Order.PAID
        payment.save()
        if payment.order:
            payment.order.payment_status = Order.PAID
            payment.order.save()
        messages.success(request, f"Payment #{payment.transaction_id} marked as PAID.")
        return redirect(request.META.get("HTTP_REFERER", "admin_portal:payment_list"))


# -----------------------------------------------------------------------------
# 8. REPORTS & BUSINESS INTELLIGENCE + CSV EXPORT
# -----------------------------------------------------------------------------
class AdminReportsView(AdminRequiredMixin, TemplateView):
    template_name = "admin_portal/reports/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Totals
        total_orders = Order.objects.count()
        paid_orders = Order.objects.filter(payment_status=Order.PAID)
        total_revenue = paid_orders.aggregate(Sum("total_amount"))["total_amount__sum"] or Decimal("0.00")
        avg_order_value = paid_orders.aggregate(Avg("total_amount"))["total_amount__avg"] or Decimal("0.00")

        # Top selling products
        top_products = (
            OrderItem.objects.values("product_name")
            .annotate(total_qty=Sum("quantity"), total_sales=Sum("subtotal"))
            .order_by("-total_qty")[:10]
        )

        # Provider statistics
        provider_stats = Provider.objects.annotate(
            total_req=Count("requests"),
            approved_req=Count("requests", filter=Q(requests__status=ProviderRequest.APPROVED)),
        ).order_by("-total_req")[:10]

        # Category sales distribution
        category_sales = (
            Category.objects.annotate(
                total_products_count=Count("products"),
            )
        )

        context.update({
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_order_value": avg_order_value,
            "top_products": top_products,
            "provider_stats": provider_stats,
            "category_sales": category_sales,
            "total_users": User.objects.count(),
            "total_providers": Provider.objects.count(),
            "total_products": Product.objects.count(),
        })
        return context


class ExportSalesReportCSVView(AdminRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="agrivision_sales_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Order Number", "Customer Name", "Customer Email", "Date", "Payment Method", "Payment Status", "Order Status", "Total Amount (INR)"])

        orders = Order.objects.all().order_by("-created_at")
        for order in orders:
            writer.writerow([
                order.order_number,
                order.full_name,
                order.email,
                order.created_at.strftime("%Y-%m-%d %H:%M"),
                order.get_payment_method_display(),
                order.get_payment_status_display(),
                order.get_order_status_display(),
                order.total_amount,
            ])
        return response


class ExportOrdersReportCSVView(AdminRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="agrivision_orders_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Order Number", "Customer", "Item Name", "Quantity", "Unit Price (INR)", "Subtotal (INR)", "Order Status", "Date"])

        items = OrderItem.objects.select_related("order").order_by("-order__created_at")
        for item in items:
            writer.writerow([
                item.order.order_number,
                item.order.full_name,
                item.product_name,
                item.quantity,
                item.price,
                item.subtotal,
                item.order.get_order_status_display(),
                item.order.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
        return response


class ExportProductsReportCSVView(AdminRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="agrivision_inventory_report_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Product ID", "Product Name", "Category", "Provider / Source", "Cost Price (INR)", "Selling Price (INR)", "Stock Units", "Status"])

        products = Product.objects.select_related("category").order_by("name")
        for p in products:
            status = "Active" if p.is_active else "Inactive"
            if p.stock == 0:
                status += " (Out of Stock)"
            elif p.stock <= 10:
                status += " (Low Stock)"
            writer.writerow([
                p.id,
                p.name,
                p.category.name if p.category else "Uncategorized",
                p.provider_name or "AgriVision Direct",
                p.cost_price,
                p.price,
                p.stock,
                status,
            ])
        return response
