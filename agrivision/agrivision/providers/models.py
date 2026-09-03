from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProviderProfile(models.Model):
    """
    Extended profile for a user who has applied to become a Provider.

    Relationship:
        User (1) ──── (1) ProviderProfile
                              │
                              ├── verification_status  (PENDING / APPROVED / REJECTED)
                              ├── farm details
                              └── ProviderRequest(s)   (product listings submitted by this provider)
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
        _("Type of Provider"), max_length=100, blank=True, default="Plant Nursery & Seeds"
    )
    description = models.TextField(_("Description"), blank=True)
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True)
    address = models.TextField(_("Address"), blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    district = models.CharField(_("District"), max_length=100, blank=True)
    state = models.CharField(_("State"), max_length=100, blank=True, default="Kerala")
    experience_years = models.CharField(_("Years of Experience"), max_length=50, blank=True)

    # License & Verification
    license_number = models.CharField(_("License Number"), max_length=100, blank=True)
    license_type = models.CharField(_("License Type"), max_length=100, blank=True)
    license_document = models.FileField(
        _("License Document"), upload_to="licenses/", blank=True, null=True
    )

    # Approval Status — default is PENDING (not APPROVED)
    verification_status = models.CharField(
        _("Verification Status"),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Provider Profile"
        verbose_name_plural = "Provider Profiles"

    def __str__(self):
        return f"{self.farm_name} ({self.user.email})"

    # ── Convenience properties ──────────────────────────────────────────────

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
    def total_products_count(self):
        """Number of product listings (ProviderRequests) submitted by this provider."""
        return self.product_requests.count()

    @property
    def approved_products_count(self):
        """Number of product listings approved by admin."""
        return self.product_requests.filter(
            status=ProviderRequest.Status.APPROVED
        ).count()

    @property
    def pending_products_count(self):
        """Number of product listings still pending admin review."""
        return self.product_requests.filter(
            status=ProviderRequest.Status.PENDING
        ).count()

    @property
    def marketplace_products(self):
        """Marketplace Products that originated from this provider's approved requests."""
        from agrivision.marketplace.models import Product
        return Product.objects.filter(provider=self)

    @property
    def marketplace_products_count(self):
        return self.marketplace_products.count()


class ProviderRequest(models.Model):
    """
    A seed or plant product submission by a Provider, pending Admin review.

    When Admin APPROVES a ProviderRequest, Admin creates/links a marketplace.Product
    and sets `created_product`.  The product is then visible in the marketplace.

    Status flow:  PENDING  →  APPROVED  (product listed)
                           →  REJECTED  (product not listed)
    """

    class Category(models.TextChoices):
        SEEDS = "Seeds", _("🌱 Seeds")
        PLANTS = "Plants", _("🌿 Plants")

    class Status(models.TextChoices):
        PENDING = "Pending", _("Pending Review")
        APPROVED = "Approved", _("Approved & Listed")
        REJECTED = "Rejected", _("Rejected")

    provider = models.ForeignKey(
        ProviderProfile,
        on_delete=models.CASCADE,
        related_name="product_requests",   # changed from "requests" to avoid confusion
    )
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=Category.choices,
        default=Category.SEEDS,
    )
    item_name = models.CharField(_("Product Name"), max_length=200)
    description = models.TextField(_("Description & Variety Notes"), blank=True)

    # Quantity & Pricing
    quantity = models.PositiveIntegerField(_("Quantity Available"), default=10)
    expected_price = models.DecimalField(
        _("Expected Unit Price (₹)"), max_digits=10, decimal_places=2
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
        choices=Status.choices,
        default=Status.PENDING,
    )
    admin_notes = models.TextField(_("Admin Feedback"), blank=True)

    # Linked Marketplace Product (set when request is approved)
    created_product = models.ForeignKey(
        "marketplace.Product",
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

    def __str__(self):
        return (
            f"{self.item_name} ({self.category}) by "
            f"{self.provider.farm_name} — {self.get_status_display()}"
        )

    @property
    def display_image(self):
        """Return the best available image URL for display."""
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        if self.category == self.Category.SEEDS:
            return (
                "https://images.unsplash.com/photo-1592417817098-8f3d6eb22509"
                "?w=400&auto=format&fit=crop&q=60"
            )
        return (
            "https://images.unsplash.com/photo-1485955900006-10f4d324d411"
            "?w=400&auto=format&fit=crop&q=60"
        )
