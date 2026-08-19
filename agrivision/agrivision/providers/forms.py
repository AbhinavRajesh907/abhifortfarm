from django import forms
from .models import ProviderProfile, ProviderRequest

class ProviderProfileForm(forms.ModelForm):
    class Meta:
        model = ProviderProfile
        fields = ['phone_number', 'address', 'company_name']

class ProviderRequestForm(forms.ModelForm):
    class Meta:
        model = ProviderRequest
        fields = ['item_name', 'quantity', 'expected_price']
