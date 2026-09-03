"""Forms and input validators for AI & Agriculture module."""

import io
from PIL import Image
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}

SOIL_CHOICES = [
    ("", _("Select Soil Type (Optional)")),
    ("Clay", _("Clay Soil (Heavy, water-retaining)")),
    ("Loam", _("Loam Soil (Fertile, balanced)")),
    ("Sandy loam", _("Sandy Loam (Well-drained, light)")),
    ("Black", _("Black / Regur Soil (Clayey, moisture-retentive)")),
    ("Alluvial", _("Alluvial Soil (Rich river basin sediment)")),
    ("Red", _("Red / Laterite Soil (Porous, iron-rich)")),
]

SEASON_CHOICES = [
    ("", _("Select Season (Optional)")),
    ("Kharif", _("Kharif (Monsoon / Summer Sowing: June - October)")),
    ("Rabi", _("Rabi (Winter Sowing: October - April)")),
    ("Zaid", _("Zaid / Summer (March - June)")),
    ("Monsoon", _("Monsoon")),
    ("Winter", _("Winter")),
    ("Summer", _("Summer")),
]


class DiseaseDetectionForm(forms.Form):
    """Image upload form for AI disease diagnosis."""

    image = forms.ImageField(
        label=_("Upload Leaf Image"),
        help_text=_("Attach a clear leaf photo (JPEG, PNG, or WEBP, max 5 MB)."),
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*", "id": "plantImageInput"}),
    )

    def clean_image(self):
        img = self.cleaned_data.get("image")
        if not img:
            raise ValidationError(_("Please select an image file."))

        if img.size > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(_("File size exceeds 5 MB. Please upload a smaller image."))

        if hasattr(img, "content_type") and img.content_type.lower() not in ALLOWED_IMAGE_MIMES:
            raise ValidationError(_("Invalid image format. Supported formats: JPEG, PNG, WEBP."))

        try:
            with Image.open(img) as pil_img:
                pil_img.verify()
                img_format = pil_img.format
        except Exception as exc:
            raise ValidationError(_("The uploaded file is not a valid or readable image.")) from exc

        if img_format not in ALLOWED_IMAGE_FORMATS:
            raise ValidationError(_("Invalid image format. Supported formats: JPEG, PNG, WEBP."))

        img.seek(0)
        return img


class SoilParamsRecommendationForm(forms.Form):
    """Agronomic recommendation form taking detailed soil and climate telemetry."""

    n = forms.DecimalField(
        label=_("Nitrogen (N)"),
        required=False,
        min_value=0,
        max_value=300,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 80 (kg/ha)"}),
        help_text=_("Nitrogen content in kg/ha (0 - 300)"),
    )
    p = forms.DecimalField(
        label=_("Phosphorus (P)"),
        required=False,
        min_value=0,
        max_value=200,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 40 (kg/ha)"}),
        help_text=_("Phosphorus content in kg/ha (0 - 200)"),
    )
    k = forms.DecimalField(
        label=_("Potassium (K)"),
        required=False,
        min_value=0,
        max_value=250,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 40 (kg/ha)"}),
        help_text=_("Potassium content in kg/ha (0 - 250)"),
    )
    ph = forms.DecimalField(
        label=_("Soil pH"),
        required=False,
        min_value=3.0,
        max_value=11.0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 6.5", "step": "0.1"}),
        help_text=_("Soil pH value (3.0 - 11.0)"),
    )
    rainfall = forms.DecimalField(
        label=_("Rainfall (mm)"),
        required=False,
        min_value=0,
        max_value=5000,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 1200 (mm)"}),
        help_text=_("Seasonal rainfall in mm (0 - 5000)"),
    )
    temperature = forms.DecimalField(
        label=_("Temperature (°C)"),
        required=False,
        min_value=-10,
        max_value=60,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g. 26 (°C)", "step": "0.5"}),
        help_text=_("Average temperature (-10 to 60 °C)"),
    )
    soil_type = forms.ChoiceField(
        label=_("Soil Texture"),
        required=False,
        choices=SOIL_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    season = forms.ChoiceField(
        label=_("Growing Season"),
        required=False,
        choices=SEASON_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        label=_("Farm Location / State"),
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kerala, Punjab, Maharashtra"}),
    )


class SeasonRecommendationForm(forms.Form):
    """Direct season-based crop recommendation form."""

    season = forms.ChoiceField(
        label=_("Select Agricultural Season"),
        choices=[c for c in SEASON_CHOICES if c[0]],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        label=_("Region / Location (Optional)"),
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Kerala"}),
    )


class SoilTypeRecommendationForm(forms.Form):
    """Direct soil-type crop recommendation form."""

    soil_type = forms.ChoiceField(
        label=_("Select Soil Type"),
        choices=[c for c in SOIL_CHOICES if c[0]],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        label=_("Region / Location (Optional)"),
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Maharashtra"}),
    )


class CropRecommendationForm(forms.Form):
    """Unified crop recommendation form."""

    soil_type = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    season = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    location = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    temperature = forms.DecimalField(required=False, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={"class": "form-control"}))
    rainfall = forms.DecimalField(required=False, max_digits=8, decimal_places=2, widget=forms.NumberInput(attrs={"class": "form-control"}))
    ph = forms.DecimalField(required=False, max_digits=4, decimal_places=2, widget=forms.NumberInput(attrs={"class": "form-control"}))
    n = forms.DecimalField(required=False, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={"class": "form-control"}))
    p = forms.DecimalField(required=False, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={"class": "form-control"}))
    k = forms.DecimalField(required=False, max_digits=6, decimal_places=2, widget=forms.NumberInput(attrs={"class": "form-control"}))


class AgricultureInfoSearchForm(forms.Form):
    """Search form for crops and plant pathology."""

    query = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Search crops, diseases, treatments..."}),
    )
    information_type = forms.ChoiceField(
        required=False,
        choices=[("", _("All Topics")), ("crop", _("Crops Only")), ("disease", _("Diseases Only"))],
        widget=forms.Select(attrs={"class": "form-select"}),
    )


class MarketPriceFilterForm(forms.Form):
    """Market price filter form."""

    crop = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Crop name..."}))
    market = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Market / Mandi..."}))
    region = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Region / State..."}))
