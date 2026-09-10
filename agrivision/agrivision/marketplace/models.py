import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    """Product category — ONLY Seeds and Plants are primary, extensible by Admin."""

    SEEDS = "Seeds"
    PLANTS = "Plants"
    ALLOWED_NAMES = [SEEDS, PLANTS]

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default="fa-seedling")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

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
        if self.category and self.category.name == "Seeds":
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
    """A placed order."""

    # Payment method choices
    COD = "cod"
    ONLINE = "online"
    PAYMENT_METHOD_CHOICES = [
        (COD, "Cash on Delivery"),
        (ONLINE, "Online Payment"),
    ]

    # Payment status choices
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PAYMENT_STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]

    # Order status choices
    ORDER_PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    ORDER_STATUS_CHOICES = [
        (ORDER_PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (PROCESSING, "Processing"),
        (SHIPPED, "Shipped"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="marketplace_orders",
    )
    order_number = models.CharField(max_length=30, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

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
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default=COD
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PENDING
    )
    order_status = models.CharField(
        max_length=20, choices=ORDER_STATUS_CHOICES, default=ORDER_PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} by {self.user.email}"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    """A single product line inside an Order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price at time of order
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.product_name and self.product:
            self.product_name = self.product.name
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
