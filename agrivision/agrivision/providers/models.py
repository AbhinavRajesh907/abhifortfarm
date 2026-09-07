from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from agrivision.marketplace.models import Category, Product


class ProviderProfile(models.Model):
    """
    Unified profile for registered agricultural providers, nurseries, and seed producers.
    Compatible with Joyal's Provider Dashboard, Santhana's Admin Portal, and Abhinav's Registration.
    """

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile",
    )

    # Farm / Business Information
    farm_name = models.CharField(_("Farm/Business Name"), max_length=200)
    provider_type = models.CharField(
        _("Type of Provider"), max_length=100, blank=True, default="Plant Nursery"
    )
    description = models.TextField(_("Short Description / Products Overview"), blank=True)
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)
    address = models.TextField(_("Personal / Residential Address"), blank=True)
    farm_address = models.TextField(_("Farm / Facility Address"), blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    district = models.CharField(_("District"), max_length=100, blank=True)
    state = models.CharField(_("State"), max_length=100, blank=True, default="Kerala")
    pincode = models.CharField(_("Pincode"), max_length=20, blank=True)
    experience_years = models.CharField(_("Years of Experience"), max_length=50, blank=True)

    # License & Verification
    license_number = models.CharField(_("License / Registration Number"), max_length=100, blank=True)
    license_type = models.CharField(_("License Type"), max_length=100, blank=True)
    issuing_authority = models.CharField(_("Issuing Authority"), max_length=255, blank=True)
    issue_date = models.DateField(_("Issue Date"), null=True, blank=True)
    expiry_date = models.DateField(_("Expiry Date"), null=True, blank=True)
    license_document = models.FileField(
        _("License Document"), upload_to="licenses/", blank=True, null=True
    )

    # Approval Status
    verification_status = models.CharField(
        _("Verification Status"),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Provider Profile"
        verbose_name_plural = "Provider Profiles"

    def __str__(self):
        return f"{self.farm_name} ({getattr(self.user, 'email', '')})"

    # ── Compatibility Properties ─────────────────────────────────────────────

    @property
    def contact_person(self):
        return getattr(self.user, "name", "") or getattr(self.user, "username", "") or "Provider Representative"

    @property
    def phone(self):
        return self.phone_number or getattr(self.user, "phone", "") or getattr(self.user, "phone_number", "")

    @property
    def email(self):
        return getattr(self.user, "email", "")

    @property
    def pin_code(self):
        return self.pincode

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.APPROVED

    @is_verified.setter
    def is_verified(self, value):
        if value:
            self.verification_status = self.VerificationStatus.APPROVED
            self.verification_date = timezone.now()
        else:
            self.verification_status = self.VerificationStatus.PENDING
            self.verification_date = None

    @property
    def is_approved(self):
        return self.verification_status == self.VerificationStatus.APPROVED

    @property
    def is_pending(self):
        return self.verification_status == self.VerificationStatus.PENDING

    @property
    def is_rejected(self):
        return self.verification_status == self.VerificationStatus.REJECTED

    @property
    def requests(self):
        """Alias for Santhana's admin portal."""
        return self.product_requests

    @property
    def supplied_products(self):
        """Alias for Santhana's admin portal."""
        return self.marketplace_products

    @property
    def total_requests_count(self):
        return self.product_requests.count()

    @property
    def total_products_count(self):
        return self.product_requests.count()

    @property
    def pending_requests_count(self):
        return self.product_requests.filter(
            models.Q(status="Pending") | models.Q(status="pending") | models.Q(status="PENDING")
        ).count()

    @property
    def pending_products_count(self):
        return self.pending_requests_count

    @property
    def approved_requests_count(self):
        return self.product_requests.filter(
            models.Q(status="Approved") | models.Q(status="approved") | models.Q(status="APPROVED")
        ).count()

    @property
    def approved_products_count(self):
        return self.approved_requests_count

    @property
    def marketplace_products(self):
        return Product.objects.filter(provider=self)

    @property
    def marketplace_products_count(self):
        return self.marketplace_products.count()


# Backward-compatible model alias for Santhana's admin portal
Provider = ProviderProfile


class ProviderRequest(models.Model):
    """
    A seed or plant product submission by a Provider, pending Admin review.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [
        (PENDING, "Pending Review"),
        (APPROVED, "Approved & Listed"),
        (REJECTED, "Rejected"),
    ]

    class CategoryChoices(models.TextChoices):
        SEEDS = "Seeds", _("🌱 Seeds")
        PLANTS = "Plants", _("🌿 Plants")

    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name="product_requests",
    )
    item_name = models.CharField(_("Product Name"), max_length=200, default="")
    product_name = models.CharField(_("Product Name (Alt)"), max_length=200, blank=True, default="")
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="provider_requests",
        null=True,
        blank=True,
    )
    category_name = models.CharField(
        _("Category Name"),
        max_length=50,
        blank=True,
        default="Seeds",
    )
    description = models.TextField(_("Description & Variety Notes"), blank=True)

    # Quantity & Pricing
    quantity = models.PositiveIntegerField(_("Quantity Available"), default=10)
    expected_price = models.DecimalField(
        _("Expected Unit Price (₹)"), max_digits=10, decimal_places=2, default=0.00
    )
    selling_price = models.DecimalField(
        _("Marketplace Selling Price (₹)"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Set by Admin when approving.",
    )

    # Images
    image = models.ImageField(
        _("Product Image"), upload_to="provider_items/", blank=True, null=True
    )
    image_url = models.URLField(
        _("Image URL (Optional)"), max_length=500, blank=True, null=True
    )

    # Admin Review
    status = models.CharField(
        _("Approval Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    admin_notes = models.TextField(_("Admin Feedback"), blank=True)
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_provider_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Linked Marketplace Product (set when request is approved)
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
        verbose_name = "Provider Product Request"
        verbose_name_plural = "Provider Product Requests"

    def save(self, *args, **kwargs):
        if not self.item_name and self.product_name:
            self.item_name = self.product_name
        elif not self.product_name and self.item_name:
            self.product_name = self.item_name
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        if self.category and self.category.name == "Seeds":
            return "https://images.unsplash.com/photo-1592417817098-8f3d6eb22509?w=400&auto=format&fit=crop&q=60"
        return "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=400&auto=format&fit=crop&q=60"


class ProviderProduct(models.Model):
    """Historical mapping of products associated with providers."""

    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name="supplied_product_links")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="provider_links")
    supplied_quantity = models.PositiveIntegerField(default=1)
    unit_procurement_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} from {self.provider.farm_name}"
