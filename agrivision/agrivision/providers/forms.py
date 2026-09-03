from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import ProviderProfile, ProviderRequest


class ProviderApplyForm(forms.ModelForm):
    """
    Form for a regular authenticated user to apply to become a Provider.
    Creates/updates their ProviderProfile with status=PENDING.
    """

    class Meta:
        model = ProviderProfile
        fields = [
            "farm_name",
            "provider_type",
            "description",
            "phone_number",
            "address",
            "city",
            "district",
            "state",
            "experience_years",
            "license_number",
            "license_type",
            "license_document",
        ]
        widgets = {
            "farm_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Green Valley Nursery"}
            ),
            "provider_type": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Plant Nursery & Seeds"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Tell us about your farm/business...",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+91 98765 43210"}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "rows": 2, "placeholder": "Street address"}
            ),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "district": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "experience_years": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. 3+ Years"}
            ),
            "license_number": forms.TextInput(attrs={"class": "form-control"}),
            "license_type": forms.TextInput(attrs={"class": "form-control"}),
            "license_document": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }
        labels = {
            "farm_name": "Farm / Business Name *",
            "phone_number": "Phone Number *",
        }

    def clean_farm_name(self):
        name = self.cleaned_data.get("farm_name", "").strip()
        if not name:
            raise ValidationError(_("Farm/Business name is required."))
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number", "").strip()
        if not phone:
            raise ValidationError(_("Phone number is required."))
        return phone


class ProviderProfileForm(forms.ModelForm):
    """
    Form for an approved Provider to update their own profile details.
    Does NOT allow changing verification_status.
    """

    class Meta:
        model = ProviderProfile
        fields = [
            "farm_name",
            "provider_type",
            "description",
            "phone_number",
            "address",
            "city",
            "district",
            "state",
            "experience_years",
        ]
        widgets = {
            "farm_name": forms.TextInput(attrs={"class": "form-control"}),
            "provider_type": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "district": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "experience_years": forms.TextInput(attrs={"class": "form-control"}),
        }


class ProviderRequestForm(forms.ModelForm):
    """
    Form for an approved Provider to submit a new seed/plant product for admin review.
    """

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
