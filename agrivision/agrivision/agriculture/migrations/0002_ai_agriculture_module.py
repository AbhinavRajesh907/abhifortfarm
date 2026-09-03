"""Migration for AI & Agriculture module extended schema.

Adds new fields to CropInformation (agronomic thresholds: min/max temp, pH, rainfall, N-P-K),
DiseaseInformation (symptoms, severity), CropRecommendation (rainfall, pH, N-P-K, JSON
input_params, recommended_crops_list), MarketPrice (region, unit), and
DiseaseDetection verbose_names.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("agriculture", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- DiseaseInformation: add symptoms and severity ---
        migrations.AddField(
            model_name="diseaseinformation",
            name="symptoms",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="diseaseinformation",
            name="severity",
            field=models.CharField(
                choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")],
                default="medium",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="diseaseinformation",
            options={
                "ordering": ["name"],
                "verbose_name": "Disease information",
                "verbose_name_plural": "Disease information",
            },
        ),

        # --- CropInformation: add agronomic threshold fields ---
        migrations.AddField(
            model_name="cropinformation",
            name="min_temp",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Min temp in °C", max_digits=5, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="max_temp",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Max temp in °C", max_digits=5, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="min_ph",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Min soil pH", max_digits=4, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="max_ph",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Max soil pH", max_digits=4, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="min_rainfall",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Min rainfall in mm", max_digits=7, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="max_rainfall",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Max rainfall in mm", max_digits=7, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="optimal_n",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Optimal Nitrogen (kg/ha)", max_digits=6, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="optimal_p",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Optimal Phosphorus (kg/ha)", max_digits=6, null=True
            ),
        ),
        migrations.AddField(
            model_name="cropinformation",
            name="optimal_k",
            field=models.DecimalField(
                blank=True, decimal_places=2, help_text="Optimal Potassium (kg/ha)", max_digits=6, null=True
            ),
        ),
        migrations.AlterField(
            model_name="cropinformation",
            name="soil_types",
            field=models.CharField(
                help_text="Comma-separated soil types (e.g. Clay, Loam, Sandy loam).",
                max_length=255,
            ),
        ),

        # --- DiseaseDetection: add verbose_names ---
        migrations.AlterModelOptions(
            name="diseasedetection",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Disease detection",
                "verbose_name_plural": "Disease detections",
            },
        ),

        # --- CropRecommendation: add rainfall, pH, NPK, JSON fields ---
        migrations.AlterField(
            model_name="croprecommendation",
            name="soil_type",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="croprecommendation",
            name="season",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="croprecommendation",
            name="location",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="rainfall",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="ph",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="n",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Nitrogen (N)"
            ),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="p",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Phosphorus (P)"
            ),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="k",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=6, null=True, verbose_name="Potassium (K)"
            ),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="input_params",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="croprecommendation",
            name="recommended_crops_list",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterModelOptions(
            name="croprecommendation",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Crop recommendation",
                "verbose_name_plural": "Crop recommendations",
            },
        ),

        # --- MarketPrice: add region and unit fields ---
        migrations.AddField(
            model_name="marketprice",
            name="region",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="marketprice",
            name="unit",
            field=models.CharField(default="quintal", max_length=50),
        ),
        migrations.AlterModelOptions(
            name="marketprice",
            options={
                "ordering": ["-observed_at", "crop__name"],
                "verbose_name": "Market price",
                "verbose_name_plural": "Market prices",
            },
        ),
    ]
