from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from agrivision.marketplace.models import Category, Product


class Provider(models.Model):
    """Profile for registered seed/plant and agricultural item providers."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile",
    )
    farm_name = models.CharField(max_length=200, help_text="Farm, Nursery, or Business Name")
    contact_person = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="Kerala")
    pin_code = models.CharField(max_length=15)
    
    is_verified = models.BooleanField(default=False, help_text="Admin verification status")
    verification_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.farm_name} ({self.contact_person})"

    @property
    def total_requests_count(self):
        return self.requests.count()

    @property
    def pending_requests_count(self):
        return self.requests.filter(status=ProviderRequest.PENDING).count()

    @property
    def approved_requests_count(self):
        return self.requests.filter(status=ProviderRequest.APPROVED).count()


class ProviderRequest(models.Model):
    """Seed/Plant/Product request submitted by a provider for Admin review."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending Review"),
        (APPROVED, "Approved & Listed"),
        (REJECTED, "Rejected"),
    ]

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="requests")
    product_name = models.CharField(max_length=200, help_text="Name of the seed, plant, or agricultural item")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="provider_requests")
    description = models.TextField(help_text="Variety details, growing requirements, and features")
    quantity = models.PositiveIntegerField(help_text="Units/Packets available")
    expected_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Expected procurement price per unit in INR")
    selling_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Admin-determined marketplace selling price"
    )
    
    image = models.ImageField(upload_to="provider_requests/", blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    admin_notes = models.TextField(blank=True, help_text="Admin feedback or internal notes")
    rejection_reason = models.TextField(blank=True, help_text="Reason given if request is rejected")
    
    # Audit trail
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_provider_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Link to resulting marketplace product upon approval
    created_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="origin_request",
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product_name} by {self.provider.farm_name} ({self.get_status_display()})"

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return "https://images.unsplash.com/photo-1592417817098-8f3d6eb22509?w=500&auto=format&fit=crop&q=60"


class ProviderProduct(models.Model):
    """Historical mapping of products associated with providers."""

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name="supplied_products")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="provider_link")
    supplied_quantity = models.PositiveIntegerField()
    unit_procurement_cost = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} from {self.provider.farm_name}"
