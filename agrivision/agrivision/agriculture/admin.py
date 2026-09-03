from django.contrib import admin

from .models import (
    CropInformation,
    CropRecommendation,
    DiseaseDetection,
    DiseaseInformation,
    MarketPrice,
)


@admin.register(DiseaseInformation)
class DiseaseInformationAdmin(admin.ModelAdmin):
    list_display = ["name", "severity"]
    list_filter = ["severity"]
    search_fields = ["name", "description", "treatment"]


@admin.register(CropInformation)
class CropInformationAdmin(admin.ModelAdmin):
    list_display = ["name", "soil_types", "seasons", "optimal_n", "optimal_p", "optimal_k"]
    search_fields = ["name", "soil_types", "seasons", "locations"]


@admin.register(DiseaseDetection)
class DiseaseDetectionAdmin(admin.ModelAdmin):
    list_display = ["user", "disease", "confidence", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["user__email", "disease__name"]
    readonly_fields = ["created_at"]


@admin.register(CropRecommendation)
class CropRecommendationAdmin(admin.ModelAdmin):
    list_display = ["user", "recommended_crop", "soil_type", "season", "location", "created_at"]
    list_filter = ["season", "soil_type", "created_at"]
    search_fields = ["user__email", "location", "recommended_crop__name"]
    readonly_fields = ["created_at"]


@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ["crop", "market", "region", "price", "unit", "currency", "observed_at", "data_source"]
    list_filter = ["data_source", "region", "market"]
    search_fields = ["crop__name", "market", "region"]
    readonly_fields = ["observed_at"]
