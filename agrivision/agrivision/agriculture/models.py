from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DiseaseInformation(models.Model):
    """Database repository of plant diseases, symptoms, treatments, and preventive measures."""

    SEVERITY_LOW = "low"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_HIGH = "high"
    SEVERITY_CHOICES = [
        (SEVERITY_LOW, _("Low")),
        (SEVERITY_MEDIUM, _("Medium")),
        (SEVERITY_HIGH, _("High")),
    ]

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    symptoms = models.TextField(blank=True)
    treatment = models.TextField()
    prevention = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_MEDIUM,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Disease information")
        verbose_name_plural = _("Disease information")

    def __str__(self):
        return self.name


class CropInformation(models.Model):
    """Agronomic crop encyclopedia with soil, season, and climate tolerance profiles."""

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField()
    cultivation_information = models.TextField()
    soil_types = models.CharField(max_length=255, help_text="Comma-separated soil types (e.g. Clay, Loam, Sandy loam).")
    seasons = models.CharField(max_length=255, help_text="Comma-separated seasons (e.g. Kharif, Rabi, Summer).")
    locations = models.CharField(blank=True, max_length=255, help_text="Optional comma-separated regions.")

    # Agronomic thresholds for scientific recommendation scoring
    min_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Min temp in °C")
    max_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Max temp in °C")
    min_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Min soil pH")
    max_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, help_text="Max soil pH")
    min_rainfall = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Min rainfall in mm")
    max_rainfall = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Max rainfall in mm")
    optimal_n = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Optimal Nitrogen (kg/ha)")
    optimal_p = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Optimal Phosphorus (kg/ha)")
    optimal_k = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Optimal Potassium (kg/ha)")

    class Meta:
        ordering = ["name"]
        verbose_name = _("Crop information")
        verbose_name_plural = _("Crop information")

    def __str__(self):
        return self.name

    @staticmethod
    def matches(value: str, choices: str) -> bool:
        """Check if a given value matches any choice in a comma-separated list."""
        if not value or not choices:
            return False
        clean_value = value.casefold().strip()
        return any(clean_value in choice.casefold().strip() or choice.casefold().strip() in clean_value for choice in choices.split(","))


class DiseaseDetection(models.Model):
    """User disease detection upload history and enriched treatment diagnosis."""

    PENDING = "pending"
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"
    STATUS_CHOICES = [
        (PENDING, _("Pending")),
        (COMPLETE, _("Complete")),
        (UNAVAILABLE, _("Model unavailable")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="disease_detections",
    )
    image = models.ImageField(upload_to="agriculture/disease-detections/")
    disease = models.ForeignKey(
        DiseaseInformation,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="detections",
    )
    confidence = models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)
    treatment = models.TextField(blank=True)
    prevention = models.TextField(blank=True)
    status = models.CharField(choices=STATUS_CHOICES, default=PENDING, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Disease detection")
        verbose_name_plural = _("Disease detections")

    def __str__(self):
        return f"Detection #{self.pk} for {self.user} - {self.disease or 'Unclassified'}"

    @property
    def confidence_percentage(self) -> float:
        if self.confidence is not None:
            return round(float(self.confidence) * 100, 1)
        return 0.0


class CropRecommendation(models.Model):
    """User crop recommendation query and ranked recommendation results."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="crop_recommendations",
    )
    soil_type = models.CharField(max_length=100, blank=True)
    season = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    temperature = models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)
    rainfall = models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)
    ph = models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)
    n = models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Nitrogen (N)")
    p = models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Phosphorus (P)")
    k = models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Potassium (K)")

    input_params = models.JSONField(default=dict, blank=True)
    recommended_crop = models.ForeignKey(
        CropInformation,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="recommendations",
    )
    recommended_crops_list = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Crop recommendation")
        verbose_name_plural = _("Crop recommendations")

    def __str__(self):
        return f"Recommendation #{self.pk} for {self.user} ({self.recommended_crop or 'No match'})"


class MarketPrice(models.Model):
    """Agricultural commodity market price directory."""

    SAMPLE = "sample"
    EXTERNAL_API = "external_api"
    DATA_SOURCE_CHOICES = [
        (SAMPLE, _("Development sample")),
        (EXTERNAL_API, _("External API")),
    ]

    crop = models.ForeignKey(
        CropInformation,
        on_delete=models.CASCADE,
        related_name="market_prices",
    )
    market = models.CharField(max_length=150)
    region = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(decimal_places=2, max_digits=12)
    unit = models.CharField(max_length=50, default="quintal")
    currency = models.CharField(default="INR", max_length=3)
    observed_at = models.DateTimeField()
    data_source = models.CharField(choices=DATA_SOURCE_CHOICES, default=SAMPLE, max_length=20)

    class Meta:
        ordering = ["-observed_at", "crop__name"]
        verbose_name = _("Market price")
        verbose_name_plural = _("Market prices")

    def __str__(self):
        return f"{self.crop.name} at {self.market} ({self.currency} {self.price}/{self.unit})"
