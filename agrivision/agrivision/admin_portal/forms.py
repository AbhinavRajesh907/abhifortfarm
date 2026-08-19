from django import forms
from django.contrib.auth import get_user_model
from agrivision.marketplace.models import Product, Category, Order, Payment
from agrivision.providers.models import Provider, ProviderRequest

User = get_user_model()


class ProductForm(forms.ModelForm):
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
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Enter detailed product specifications, seed germination rates, or planting guide..."}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "cost_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "low_stock_threshold": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "image": forms.FileInput(attrs={"class": "form-control"}),
            "image_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://images.unsplash.com/..."}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "icon"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Fertilizers"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Category description..."}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "fa-seedling, fa-leaf, fa-flask, fa-tools"}),
        }


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
            "contact_person",
            "phone",
            "email",
            "address",
            "city",
            "district",
            "state",
            "pin_code",
            "is_verified",
        ]
        widgets = {
            "farm_name": forms.TextInput(attrs={"class": "form-control"}),
            "contact_person": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "district": forms.TextInput(attrs={"class": "form-control"}),
            "state": forms.TextInput(attrs={"class": "form-control"}),
            "pin_code": forms.TextInput(attrs={"class": "form-control"}),
            "is_verified": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
