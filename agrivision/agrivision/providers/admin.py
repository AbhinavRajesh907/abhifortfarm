from django.contrib import admin
from django.utils.html import format_html

from .models import ProviderProfile, ProviderRequest


class ProviderRequestInline(admin.TabularInline):
    model = ProviderRequest
    extra = 0
    fields = ["item_name", "category", "quantity", "expected_price", "status", "created_at"]
    readonly_fields = ["created_at"]
    show_change_link = True


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = [
        "farm_name",
        "user",
        "phone_number",
        "city",
        "verification_status_badge",
        "created_at",
    ]
    list_filter = ["verification_status", "state", "created_at"]
    search_fields = ["user__email", "farm_name", "phone_number"]
    readonly_fields = ["created_at", "updated_at", "user"]
    list_editable = ["phone_number"]
    inlines = [ProviderRequestInline]

    fieldsets = (
        (
            "User Account",
            {
                "fields": ("user",),
            },
        ),
        (
            "Farm / Business Information",
            {
                "fields": (
                    "farm_name",
                    "provider_type",
                    "description",
                    "experience_years",
                ),
            },
        ),
        (
            "Contact & Location",
            {
                "fields": (
                    "phone_number",
                    "address",
                    "city",
                    "district",
                    "state",
                ),
            },
        ),
        (
            "License Details",
            {
                "fields": (
                    "license_number",
                    "license_type",
                    "license_document",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Approval Status",
            {
                "fields": (
                    "verification_status",
                    "rejection_reason",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Status")
    def verification_status_badge(self, obj):
        colours = {
            "APPROVED": "green",
            "PENDING": "orange",
            "REJECTED": "red",
        }
        colour = colours.get(obj.verification_status, "grey")
        label = obj.get_verification_status_display()
        return format_html(
            '<span style="color:{};font-weight:bold;">● {}</span>',
            colour,
            label,
        )

    actions = ["approve_providers", "reject_providers"]

    @admin.action(description="✅ Approve selected providers")
    def approve_providers(self, request, queryset):
        updated = queryset.update(
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
            rejection_reason="",
        )
        self.message_user(request, f"{updated} provider(s) approved.")

    @admin.action(description="❌ Reject selected providers")
    def reject_providers(self, request, queryset):
        updated = queryset.update(
            verification_status=ProviderProfile.VerificationStatus.REJECTED,
        )
        self.message_user(request, f"{updated} provider(s) rejected.")


@admin.register(ProviderRequest)
class ProviderRequestAdmin(admin.ModelAdmin):
    list_display = [
        "item_name",
        "provider",
        "category",
        "quantity",
        "expected_price",
        "selling_price",
        "status",
        "created_at",
    ]
    list_filter = ["status", "category", "created_at"]
    search_fields = ["item_name", "provider__user__email", "provider__farm_name"]
    list_editable = ["status", "selling_price"]
    readonly_fields = ["created_at", "updated_at", "provider"]

    fieldsets = (
        (
            "Product Information",
            {
                "fields": (
                    "provider",
                    "item_name",
                    "category",
                    "description",
                ),
            },
        ),
        (
            "Pricing & Stock",
            {
                "fields": (
                    "quantity",
                    "expected_price",
                    "selling_price",
                ),
            },
        ),
        (
            "Images",
            {
                "fields": ("image", "image_url"),
            },
        ),
        (
            "Admin Review",
            {
                "fields": (
                    "status",
                    "admin_notes",
                    "created_product",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["approve_requests", "reject_requests"]

    @admin.action(description="✅ Approve selected product requests")
    def approve_requests(self, request, queryset):
        updated = queryset.update(status=ProviderRequest.Status.APPROVED)
        self.message_user(request, f"{updated} product request(s) approved.")

    @admin.action(description="❌ Reject selected product requests")
    def reject_requests(self, request, queryset):
        updated = queryset.update(status=ProviderRequest.Status.REJECTED)
        self.message_user(request, f"{updated} product request(s) rejected.")
