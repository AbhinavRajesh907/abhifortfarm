from django import forms
from django.contrib.auth import get_user_model
from agrivision.marketplace.models import Product, Category, Order, Payment, RefundRequest
from agrivision.providers.models import Provider, ProviderRequest

User = get_user_model()


class ProductForm(forms.ModelForm):
    new_category_name = forms.CharField(
        label="Or Create New Category",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "e.g. Bonsai Plants, Fruit Tree Saplings..."}
        ),
        help_text="Leave blank to use selected category, or type to create a new category.",
    )
    new_category_type = forms.ChoiceField(
        label="New Category Classification",
        choices=[
            ("Plants", "🌿 Plant / Sapling"),
            ("Seeds", "🌱 Seed Variety"),
            ("Other", "📦 Farming Supply"),
        ],
        initial="Plants",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "provider_name",
            "description",
            "price",
            "cost_price",
            "stock",
            "low_stock_threshold",
            "image",
            "image_url",
            "is_active",
            "is_featured",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Hybrid Tomato F1 Seeds"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "provider_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. GreenRoots Nursery"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter detailed plant description, variety traits, sunlight, watering, soil, and care instructions..."}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "cost_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "low_stock_threshold": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://images.unsplash.com/..."}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("category_type", "name")
        self.fields["category"].required = False
        self.fields["category"].empty_label = "-- Select an Existing Category --"

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        new_cat_name = cleaned_data.get("new_category_name", "").strip()
        new_cat_type = cleaned_data.get("new_category_type") or Category.PLANTS

        if new_cat_name:
            parent_cat = Category.objects.filter(name=new_cat_type, parent__isnull=True).first()
            category, _ = Category.objects.get_or_create(
                name=new_cat_name,
                defaults={
                    "category_type": new_cat_type,
                    "parent": parent_cat,
                    "description": f"{new_cat_name} ({new_cat_type})",
                },
            )
            cleaned_data["category"] = category
        elif not category:
            self.add_error("category", "Please select a category or enter a new category name.")

        description = cleaned_data.get("description", "").strip()
        if not description:
            self.add_error("description", "Please provide a detailed description and care guide.")

        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "category_type", "parent", "description", "icon", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Vegetable Seeds"}),
            "category_type": forms.Select(attrs={"class": "form-select"}),
            "parent": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Category description..."}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "fa-seedling, fa-leaf, fa-flask, fa-tools"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = Category.objects.filter(parent__isnull=True).exclude(pk=self.instance.pk if self.instance.pk else None)
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "-- None (Top-level Parent Category) --"


class RefundProcessForm(forms.Form):
    STATUS_CHOICES = [
        (RefundRequest.RefundStatus.APPROVED, "Approve Refund"),
        (RefundRequest.RefundStatus.REJECTED, "Reject Refund"),
    ]
    decision = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    refund_amount = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Approved refund amount in INR"})
    )
    is_restocked = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Check if goods were returned in undamaged / resellable condition to add back to provider stock."
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Internal audit note or explanation to customer..."})
    )


class ProviderRequestApproveForm(forms.Form):
    selling_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Enter catalog retail price"}),
        help_text="The price customers will pay on the marketplace."
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional internal approval notes..."})
    )


class ProviderRequestRejectForm(forms.Form):
    rejection_reason = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Explain to provider why this request was not approved..."}),
        help_text="This will be shared with the provider."
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Optional internal audit notes..."})
    )


class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["order_status", "payment_status"]
        widgets = {
            "order_status": forms.Select(attrs={"class": "form-select"}),
            "payment_status": forms.Select(attrs={"class": "form-select"}),
        }


class QuickStockAdjustmentForm(forms.Form):
    ADJUSTMENT_CHOICES = [
        ("add", "Add Stock (+ units)"),
        ("set", "Set Exact Stock (= units)"),
        ("subtract", "Reduce Stock (- units)"),
    ]
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Units"})
    )
    note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. New shipment arrived / Damaged stock"})
    )


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "is_active", "is_staff", "is_superuser"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_superuser": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ProviderProfileForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = [
            "farm_name",
            "provider_type",
            "phone_number",
            "address",
            "city",
            "district",
            "state",
            "pincode",
            "verification_status",
            "license_number",
            "license_type",
            "issuing_authority",
            "issue_date",
            "expiry_date",
        ]
        widgets = {
            "farm_name": forms.TextInput(attrs={"class": "form-control"}),
            "provider_type": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "district": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "pincode": forms.TextInput(attrs={"class": "form-control"}),
            "verification_status": forms.Select(attrs={"class": "form-select"}),
            "license_number": forms.TextInput(attrs={"class": "form-control"}),
            "license_type": forms.TextInput(attrs={"class": "form-control"}),
            "issuing_authority": forms.TextInput(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "expiry_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }
