from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import ProviderProfile, ProviderRequest

PROVIDER_TYPE_CHOICES = [
    ("Plant Nursery", "Plant Nursery"),
    ("Seed Producer", "Seed Producer"),
    ("Organic Farm", "Organic Farm"),
    ("Plant & Seed Supplier", "Plant & Seed Supplier"),
    ("Agricultural Cooperative", "Agricultural Cooperative"),
    ("Fruit & Vegetable Grower", "Fruit & Vegetable Grower"),
]


class ProviderProfileForm(forms.ModelForm):
    """
    Form for editing Provider profile, structured into 3 sections:
      1. Personal & Contact Details
      2. Farm & Business Details
      3. License & Verification Details
    """

    full_name = forms.CharField(
        label=_("Full Name"),
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Full Name"}
        ),
    )
    email = forms.EmailField(
        label=_("Email Address"),
        required=False,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email Address"}
        ),
    )

    provider_type = forms.CharField(
        label=_("Provider Type"),
        required=False,
        initial="Plant Nursery",
        widget=forms.Select(choices=PROVIDER_TYPE_CHOICES, attrs={"class": "form-select"}),
    )

    issue_date = forms.DateField(
        label=_("Issue Date"),
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "dd-mm-yyyy"}
        ),
    )
    expiry_date = forms.DateField(
        label=_("Expiry Date"),
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date", "placeholder": "dd-mm-yyyy"}
        ),
    )

    class Meta:
        model = ProviderProfile
        fields = [
            # Section 1
            "phone_number",
            "address",
            "city",
            "state",
            "pincode",
            # Section 2
            "farm_name",
            "provider_type",
            "farm_address",
            "experience_years",
            "description",
            # Section 3
            "license_number",
            "license_type",
            "issuing_authority",
            "issue_date",
            "expiry_date",
            "license_document",
        ]
        widgets = {
            # Section 1
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone Number"}
            ),
            "address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Street Address / Location"}
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "City"}
            ),
            "state": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "State"}
            ),
            "pincode": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Pincode"}
            ),
            # Section 2
            "farm_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Farm or Business Name"}
            ),
            "farm_address": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Farm / Facility Location Address"}
            ),
            "experience_years": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 5 Years"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Tell us briefly about your agricultural products or farm...",
                }
            ),
            # Section 3
            "license_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "License / Registration Number"}
            ),
            "license_type": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "License Type (e.g. Trade License, Seed Dealer License)"}
            ),
            "issuing_authority": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Issuing Authority (e.g. Dept of Agriculture)"}
            ),
            "license_document": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.pdf"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["full_name"].initial = self.instance.user.name or ""
            self.fields["email"].initial = self.instance.user.email or ""

    def save(self, commit=True):
        profile = super().save(commit=False)
        full_name = self.cleaned_data.get("full_name")
        email = self.cleaned_data.get("email")
        if getattr(profile, "user_id", None) is not None:
            user = profile.user
            if full_name:
                user.name = full_name
            if email and user.email != email:
                user.email = email
            user.save()
        if commit:
            profile.save()
        return profile


class ProviderApplyForm(ProviderProfileForm):
    """Form for a new user to apply to become a Provider."""
    pass


class ProviderRequestForm(forms.ModelForm):
    """Form for an approved Provider to submit a new seed/plant product for admin review."""

    class Meta:
        model = ProviderRequest
        fields = [
            "category",
            "item_name",
            "description",
            "quantity",
            "expected_price",
            "image",
            "image_url",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "item_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Tomato Seeds (Hybrid)"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Variety details, growing tips, packaging info…",
                }
            ),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "placeholder": "Units available"}
            ),
            "expected_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "₹ per unit",
                }
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://… (optional, if no upload)",
                }
            ),
        }

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is not None and qty < 1:
            raise ValidationError(_("Quantity must be at least 1."))
        return qty

    def clean_expected_price(self):
        price = self.cleaned_data.get("expected_price")
        if price is not None and price <= 0:
            raise ValidationError(_("Price must be greater than zero."))
        return price
