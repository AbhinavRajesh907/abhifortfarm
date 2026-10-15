import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Product category supporting Seeds and Plants hierarchy, extensible by Admin."""

    SEEDS = "Seeds"
    PLANTS = "Plants"
    CATEGORY_TYPE_CHOICES = [
        (SEEDS, "Seeds"),
        (PLANTS, "Plants"),
        ("Other", "Other"),
    ]

    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES, default=SEEDS)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
        help_text="Optional parent category for subcategories (e.g. Vegetable Seeds -> Seeds)"
    )
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default="fa-seedling")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["category_type", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        if self.parent:
            self.category_type = self.parent.category_type
        elif self.category_type == self.SEEDS and ("plant" in self.name.lower()):
            self.category_type = self.PLANTS
        elif self.category_type == self.PLANTS and ("seed" in self.name.lower()):
            self.category_type = self.SEEDS
        super().save(*args, **kwargs)

    @property
    def is_seed_category(self):
        return self.category_type == self.SEEDS or "seed" in self.name.lower()

    @property
    def is_plant_category(self):
        return self.category_type == self.PLANTS or "plant" in self.name.lower()

    @property
    def product_count(self):
        return self.products.count()


class LocalProvider(models.Model):
    """Local provider mapping model for legacy/multi-provider testing."""

    name = models.CharField(max_length=200)
    business_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    branch_name = models.CharField(max_length=100, blank=True)
    branch_location = models.CharField(max_length=100, blank=True)
    branch_address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.business_name or self.name


class Product(models.Model):
    """A seed or plant product available in the marketplace."""

    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    
    # Provider who supplies this product
    provider = models.ForeignKey(
        "providers.ProviderProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketplace_products",
        verbose_name="Provider",
    )
    provider_name = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        help_text="Provider or Farm name if supplied by provider"
    )
    provider_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplied_products",
    )

    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Selling price in INR")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Procurement cost")
    stock = models.PositiveIntegerField(default=0, help_text="Available inventory units")
    low_stock_threshold = models.PositiveIntegerField(default=10, help_text="Alert threshold")
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.provider and not self.provider_name:
            self.provider_name = getattr(self.provider, "farm_name", "")
        if self.provider and not self.provider_user and hasattr(self.provider, "user"):
            self.provider_user = self.provider.user
        super().save(*args, **kwargs)

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        return self.stock <= 0

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        if self.category and self.category.category_type == Category.SEEDS:
            return "https://images.unsplash.com/photo-1592417817098-8f3d6eb22509?w=400&auto=format&fit=crop&q=60"
        return "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=400&auto=format&fit=crop&q=60"


class Cart(models.Model):
    """Shopping cart — one per user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.email}"

    def get_total(self):
        return sum(item.get_subtotal() for item in self.items.all())

    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    """A single product line inside a Cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    def get_subtotal(self):
        return self.product.price * self.quantity


class Order(models.Model):
    """A placed order supporting 3-tier payment options and status tracking."""

    # Payment method choices
    COD = "cod"
    ONLINE = "online"
    HALF_COD = "half_cod"
    PAYMENT_METHOD_CHOICES = [
        (ONLINE, "Full Online Payment"),
        (HALF_COD, "50% Online + 50% Cash on Delivery"),
        (COD, "Cash on Delivery"),
    ]

    # Payment status choices
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    COD_PENDING = "cod_pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    PAYMENT_STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PARTIALLY_PAID, "Partially Paid (50% Online)"),
        (PAID, "Paid in Full"),
        (COD_PENDING, "COD Pending"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
        (PARTIALLY_REFUNDED, "Partially Refunded"),
    ]

    # Order status choices
    ORDER_PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUND_REQUESTED = "refund_requested"
    REFUNDED = "refunded"
    ORDER_STATUS_CHOICES = [
        (ORDER_PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (PROCESSING, "Processing"),
        (SHIPPED, "Shipped"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
        (REFUND_REQUESTED, "Refund Requested"),
        (REFUNDED, "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_orders",
    )
    order_number = models.CharField(max_length=30, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    online_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    cod_amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Delivery information
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    delivery_address = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    pin_code = models.CharField(max_length=15)
    notes = models.TextField(blank=True)

    # Payment & Status
    HALF_PAID = PARTIALLY_PAID
    REFUND_NONE = "none"
    REFUND_REQUESTED = "refund_requested"
    REFUND_PENDING = "refund_pending"
    REFUND_APPROVED = "refund_approved"
    REFUND_REJECTED = "refund_rejected"
    REFUND_STATUS_CHOICES = [
        (REFUND_NONE, "No Refund"),
        (REFUND_REQUESTED, "Refund Requested"),
        (REFUND_PENDING, "Refund Processing"),
        (REFUND_APPROVED, "Refund Approved"),
        (REFUND_REJECTED, "Refund Rejected"),
    ]

    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default=COD
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PENDING
    )
    order_status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default=ORDER_PENDING
    )
    refund_status = models.CharField(
        max_length=30, choices=REFUND_STATUS_CHOICES, default=REFUND_NONE, blank=True
    )
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} by {self.user.email}"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def can_cancel(self):
        """User can cancel if order is in Pending or Confirmed state before dispatch."""
        return self.order_status in [self.ORDER_PENDING, self.CONFIRMED]

    @property
    def can_request_refund(self):
        """User can request refund if order is Delivered and not already refunded/requested."""
        return (
            self.order_status == self.DELIVERED
            and not self.refund_requests.filter(
                status__in=["REQUESTED", "UNDER_REVIEW", "APPROVED", "REFUNDED"]
            ).exists()
        )


class OrderItem(models.Model):
    """A single product line inside an Order with provider isolation."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.ForeignKey(
        "providers.ProviderProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    provider_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="provider_order_items",
    )
    product_name = models.CharField(max_length=200, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of order
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.product_name and self.product:
            self.product_name = self.product.name
        if not self.provider and self.product and self.product.provider:
            self.provider = self.product.provider
        if not self.provider_user and self.product and self.product.provider_user:
            self.provider_user = self.product.provider_user
        if not self.subtotal and self.price and self.quantity:
            self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} × {self.product_name or (self.product.name if self.product else 'Item')}"


class Payment(models.Model):
    """Detailed payment record for transactions."""

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment_record")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments")
    transaction_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    payment_method = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=Order.PAYMENT_STATUS_CHOICES, default=Order.PENDING)
    payment_date = models.DateTimeField(auto_now_add=True)
    gateway_response = models.TextField(blank=True, help_text="Raw or JSON response from payment gateway")

    def __str__(self):
        return f"Payment #{self.transaction_id} — ₹{self.amount} ({self.status})"


class StockHistory(models.Model):
    """Audit log for every stock quantity change across products."""

    class ChangeType(models.TextChoices):
        INITIAL = "INITIAL", _("Initial Stock")
        ADDED = "ADDED", _("Stock Added")
        REMOVED = "REMOVED", _("Stock Removed")
        ORDER = "ORDER", _("Order Deduction")
        CANCELLATION = "CANCELLATION", _("Order Cancellation Restock")
        REFUND_RESTOCK = "REFUND_RESTOCK", _("Refund Restock")
        MANUAL = "MANUAL", _("Manual Adjustment")

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_history")
    provider = models.ForeignKey(
        "providers.ProviderProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_history_records",
    )
    previous_stock = models.PositiveIntegerField()
    quantity_changed = models.IntegerField(help_text="Positive for addition, negative for deduction")
    new_stock = models.PositiveIntegerField()
    change_type = models.CharField(max_length=30, choices=ChangeType.choices, default=ChangeType.MANUAL)
    reason = models.TextField(blank=True)
    related_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_logs"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stock History"
        verbose_name_plural = "Stock Histories"

    def __str__(self):
        return f"{self.product.name}: {self.previous_stock} -> {self.new_stock} ({self.get_change_type_display()})"


class RefundRequest(models.Model):
    """Customer refund requests with reason capture and admin resolution."""

    class ReasonChoices(models.TextChoices):
        DAMAGED = "DAMAGED", _("Product damaged")
        WRONG_PRODUCT = "WRONG_PRODUCT", _("Wrong product received")
        NOT_RECEIVED = "NOT_RECEIVED", _("Product not received")
        POOR_QUALITY = "POOR_QUALITY", _("Poor quality")
        INCORRECT_QTY = "INCORRECT_QTY", _("Incorrect quantity")
        DIFFERENT_DESC = "DIFFERENT_DESC", _("Product different from description")
        OTHER = "OTHER", _("Other")

    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", _("Pending Review")
        REQUESTED = "REQUESTED", _("Requested")
        UNDER_REVIEW = "UNDER_REVIEW", _("Under Review")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        PROCESSING = "PROCESSING", _("Processing")
        REFUNDED = "REFUNDED", _("Refunded")
        CANCELLED = "CANCELLED", _("Cancelled")

    RefundReason = ReasonChoices
    RefundStatus = StatusChoices

    refund_number = models.CharField(max_length=30, unique=True, default=uuid.uuid4)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refund_requests")
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, null=True, blank=True, related_name="refund_requests"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refund_requests")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=50, choices=ReasonChoices.choices, default=ReasonChoices.DAMAGED)
    custom_reason = models.TextField(blank=True, help_text="Custom reason explanation if Other is chosen")
    additional_description = models.TextField(blank=True)
    status = models.CharField(max_length=30, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    is_restocked = models.BooleanField(
        default=False, help_text="True if returned items are confirmed resellable and restored to stock"
    )
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_refund_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def requested_amount(self):
        return self.amount

    @requested_amount.setter
    def requested_amount(self, val):
        self.amount = val

    @property
    def refund_amount(self):
        return self.amount

    @refund_amount.setter
    def refund_amount(self, val):
        self.amount = val

    @property
    def processed_by(self):
        return self.reviewed_by

    @processed_by.setter
    def processed_by(self, user):
        self.reviewed_by = user

    @property
    def processed_at(self):
        return self.reviewed_at

    @processed_at.setter
    def processed_at(self, dt):
        self.reviewed_at = dt

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Refund Request"
        verbose_name_plural = "Refund Requests"

    def __str__(self):
        return f"Refund #{self.refund_number} for Order #{self.order.order_number} ({self.get_status_display()})"
