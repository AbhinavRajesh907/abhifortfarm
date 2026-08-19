from django.contrib import admin
from .models import ProviderProfile, ProviderRequest

@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'phone_number']
    search_fields = ['user__email', 'company_name']

@admin.register(ProviderRequest)
class ProviderRequestAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'provider', 'quantity', 'expected_price', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['item_name', 'provider__user__email']
    list_editable = ['status']
