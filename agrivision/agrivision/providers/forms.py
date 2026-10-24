import re
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from agrivision.marketplace.models import Category, Product
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

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name", "").strip()
        if full_name:
            if not re.match(r"^[a-zA-Z\s.'-]+$", full_name):
                raise ValidationError(_("Full name should only contain alphabetic characters and spaces."))
            if len(full_name) < 2:
                raise ValidationError(_("Full name must be at least 2 characters long."))
        return full_name

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number", "").strip()
        if phone:
            if not re.match(r"^[6-9]\d{9}$", phone):
                raise ValidationError(_("Phone number must contain numbers only (10 digits starting with 6-9)."))
        return phone

    def clean_city(self):
        city = self.cleaned_data.get("city", "").strip()
        if city:
            if not re.match(r"^[a-zA-Z\s.-]+$", city):
                raise ValidationError(_("City name should only contain alphabetic characters."))
        return city

    def clean_state(self):
        state = self.cleaned_data.get("state", "").strip()
        if state:
            if not re.match(r"^[a-zA-Z\s.-]+$", state):
                raise ValidationError(_("State name should only contain alphabetic characters."))
        return state

    def clean_pincode(self):
        pincode = self.cleaned_data.get("pincode", "").strip()
        if pincode:
            if not re.match(r"^\d{6}$", pincode):
                raise ValidationError(_("Pincode must contain numbers only (6 digits)."))
        return pincode

    def clean_issue_date(self):
        issue_date = self.cleaned_data.get("issue_date")
        if issue_date and issue_date > timezone.now().date():
            raise ValidationError(
                _("License issue date cannot be in the future. Please select today's date or an earlier date.")
            )
        return issue_date

    def clean(self):
        cleaned_data = super().clean()
        issue_date = cleaned_data.get("issue_date")
        expiry_date = cleaned_data.get("expiry_date")
        if issue_date and expiry_date and expiry_date <= issue_date:
            self.add_error("expiry_date", _("License expiry date must be after the issue date."))
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today_str = timezone.now().date().isoformat()
        if "issue_date" in self.fields:
            self.fields["issue_date"].widget.attrs["max"] = today_str
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
    """Form for an approved Provider to submit a new plant or seed product."""

    PRODUCT_TYPE_PLANT = "Plants"
    PRODUCT_TYPE_SEED = "Seeds"
    PRODUCT_TYPE_CHOICES = [
        (PRODUCT_TYPE_PLANT, _("🌿 Plant")),
        (PRODUCT_TYPE_SEED, _("🌱 Seed")),
    ]

    product_type = forms.ChoiceField(
        label=_("Product Type"),
        choices=PRODUCT_TYPE_CHOICES,
        initial=PRODUCT_TYPE_PLANT,
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-lg", "id": "id_product_type"}),
    )

    # Seed-specific helper fields (optional, rich details)
    seed_variety = forms.CharField(
        label=_("Seed Variety / Strain"),
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. F1 Hybrid, Heirloom, Certified Desi Seeds"}
        ),
    )
    germination_rate = forms.CharField(
        label=_("Germination Rate / Purity"),
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. > 85% Germination, 98% Purity"}
        ),
    )
    sowing_season = forms.CharField(
        label=_("Sowing Season"),
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. Kharif (June-July), Rabi (Oct-Nov), All Seasons"}
        ),
    )
    harvest_duration = forms.CharField(
        label=_("Days to Harvest / Maturity"),
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. 60 - 75 Days"}
        ),
    )
    available_packets = forms.IntegerField(
        label=_("Available Packets"),
        required=False,
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 1,
                "step": 1,
                "placeholder": "e.g. 10, 25, 50, 100 packets",
                "id": "id_available_packets",
            }
        ),
        help_text=_("Number of seed packets available for sale. Must be a positive whole number."),
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label="-- Select Category --",
        widget=forms.Select(attrs={"class": "form-select form-select-lg", "id": "id_category"}),
        label=_("Category"),
    )

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
            "category": forms.Select(attrs={"class": "form-select form-select-lg", "id": "id_category"}),
            "item_name": forms.TextInput(
                attrs={"class": "form-control form-control-lg", "placeholder": "e.g. Grafted Alphonso Mango Plantlet, Hybrid Tomato F1 Seeds..."}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter detailed plant description, variety specifications, sunlight & watering guidelines, pot size / sapling height, soil requirements...",
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
                    "placeholder": "https://… (optional, if no image file)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("category_type", "name")
        self.fields["category"].required = False
        self.fields["quantity"].required = False
        if self.instance and self.instance.pk and self.instance.category:
            self.fields["category"].initial = self.instance.category
            if self.instance.category.category_type == "Seeds" or "seed" in self.instance.category.name.lower():
                self.fields["product_type"].initial = self.PRODUCT_TYPE_SEED
            else:
                self.fields["product_type"].initial = self.PRODUCT_TYPE_PLANT

    def clean_quantity(self):
        qty = self.cleaned_data.get("quantity")
        if qty is not None and qty < 1:
            raise ValidationError(_("Quantity must be at least 1."))
        return qty

    def clean_available_packets(self):
        val = self.cleaned_data.get("available_packets")
        if val is not None and val <= 0:
            raise ValidationError(_("Available packets must be a positive whole number greater than 0."))
        return val

    def clean_expected_price(self):
        price = self.cleaned_data.get("expected_price")
        if price is not None and price <= 0:
            raise ValidationError(_("Price must be greater than zero."))
        return price

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get("product_type")
        category = cleaned_data.get("category")
        item_name = cleaned_data.get("item_name", "").strip()

        # If category is provided, auto-sync product_type if not explicitly set
        if category:
            if category.category_type == Category.SEEDS or "seed" in category.name.lower():
                if not product_type:
                    product_type = self.PRODUCT_TYPE_SEED
                    cleaned_data["product_type"] = product_type
            elif category.category_type == Category.PLANTS or "plant" in category.name.lower():
                if not product_type:
                    product_type = self.PRODUCT_TYPE_PLANT
                    cleaned_data["product_type"] = product_type

        if not product_type:
            if "seed" in item_name.lower():
                product_type = self.PRODUCT_TYPE_SEED
            else:
                product_type = self.PRODUCT_TYPE_PLANT
            cleaned_data["product_type"] = product_type

        # Validate packet quantity for Seed products vs quantity for Plant products
        if product_type == self.PRODUCT_TYPE_SEED:
            raw_packets = self.data.get("available_packets")
            available_packets = cleaned_data.get("available_packets")

            # Check for decimals or negative numbers in raw input
            if raw_packets is not None and str(raw_packets).strip() != "":
                raw_str = str(raw_packets).strip()
                if "." in raw_str:
                    self.add_error("available_packets", _("Available packets must be a positive whole number without decimals."))
                else:
                    try:
                        int_val = int(raw_str)
                        if int_val <= 0:
                            self.add_error("available_packets", _("Available packets must be greater than zero."))
                    except ValueError:
                        self.add_error("available_packets", _("Enter a valid whole number of packets."))

            # Mandatory field check for Seed
            if available_packets is None or available_packets <= 0:
                # Support fallback to 'quantity' if submitted by existing tests/scripts
                fallback_qty = cleaned_data.get("quantity")
                if fallback_qty and fallback_qty > 0 and (raw_packets is None or str(raw_packets).strip() == ""):
                    available_packets = fallback_qty
                    cleaned_data["available_packets"] = fallback_qty
                else:
                    if "available_packets" not in self.errors:
                        self.add_error("available_packets", _("Available Packets is mandatory for seed products."))
            
            if available_packets and available_packets > 0:
                cleaned_data["quantity"] = available_packets
        else:
            # For plants, ensure quantity is valid
            plant_qty = cleaned_data.get("quantity")
            if not plant_qty or plant_qty <= 0:
                self.add_error("quantity", _("Please specify a valid quantity of plants available."))

        # Map product_type dropdown to Category (if category wasn't explicitly provided)
        if not category:
            if product_type == self.PRODUCT_TYPE_SEED:
                category, created = Category.objects.get_or_create(
                    name="Seeds",
                    defaults={"category_type": Category.SEEDS, "description": "Agricultural and garden seeds"}
                )
            else:
                category, created = Category.objects.get_or_create(
                    name="Plants",
                    defaults={"category_type": Category.PLANTS, "description": "Live plants and nursery saplings"}
                )
            cleaned_data["category"] = category

        # Enrich description with seed details if seed helper fields are provided
        description = cleaned_data.get("description", "").strip()
        if product_type == self.PRODUCT_TYPE_SEED:
            seed_details = []
            if cleaned_data.get("seed_variety"):
                seed_details.append(f"• Variety: {cleaned_data['seed_variety'].strip()}")
            if cleaned_data.get("germination_rate"):
                seed_details.append(f"• Germination Rate: {cleaned_data['germination_rate'].strip()}")
            if cleaned_data.get("sowing_season"):
                seed_details.append(f"• Sowing Season: {cleaned_data['sowing_season'].strip()}")
            if cleaned_data.get("harvest_duration"):
                seed_details.append(f"• Days to Harvest: {cleaned_data['harvest_duration'].strip()}")
            if seed_details:
                prefix = "\n".join(seed_details)
                if description and not any(k in description for k in seed_details):
                    description = f"{prefix}\n\n{description}"
                elif not description:
                    description = prefix
                cleaned_data["description"] = description

        if not description:
            if product_type == self.PRODUCT_TYPE_SEED:
                self.add_error("description", _("Please describe the seed variety, growing instructions, and number of seeds per packet."))
            else:
                self.add_error("description", _("Please provide a description and care details for this plant."))

        return cleaned_data


class ProductEditForm(forms.ModelForm):
    """Form for an approved Provider to edit an existing plant or seed product."""
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        empty_label="-- Select Category --",
        widget=forms.Select(attrs={"class": "form-select form-select-lg", "id": "id_category"}),
        label=_("Category"),
    )

    class Meta:
        model = Product
        fields = ["name", "category", "description", "price", "stock", "image", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select form-select-lg", "id": "id_category"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter detailed plant description, care instructions, soil, sunlight, and watering guidance...",
                }
            ),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("category_type", "name")
        if self.instance and self.instance.pk and self.instance.category:
            self.fields["category"].initial = self.instance.category
            cat = self.instance.category
            if cat.category_type == "Seeds" or "seed" in cat.name.lower():
                self.fields["stock"].label = _("Available Packets")
                self.fields["stock"].help_text = _("Total number of seed packets available for sale.")
                self.fields["description"].widget.attrs["placeholder"] = _(
                    "Describe the seed variety, growing instructions, and number of seeds per packet."
                )
            else:
                self.fields["stock"].label = _("Available Quantity / Stock (Units)")
                self.fields["stock"].help_text = _("Number of plants or saplings in inventory.")

    def clean_category(self):
        category = self.cleaned_data.get("category")
        if not category and self.instance and self.instance.category_id:
            category = self.instance.category
        if not category:
            raise ValidationError(_("Please select a category."))
        return category

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price <= 0:
            raise ValidationError(_("Price must be greater than zero."))
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get("stock")
        if stock is not None and stock < 0:
            raise ValidationError(_("Stock cannot be negative."))
        return stock

    def clean(self):
        cleaned_data = super().clean()
        description = cleaned_data.get("description", "").strip()
        if not description:
            self.add_error("description", _("Please provide a description and care details."))
        return cleaned_data


