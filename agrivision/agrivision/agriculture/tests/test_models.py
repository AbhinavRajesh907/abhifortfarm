import pytest
from decimal import Decimal

from agrivision.agriculture.models import (
    CropInformation,
    CropRecommendation,
    DiseaseDetection,
    DiseaseInformation,
    MarketPrice,
)

pytestmark = pytest.mark.django_db


def test_crop_and_disease_information_creation():
    crop = CropInformation.objects.create(
        name="Rice",
        description="A cereal crop.",
        cultivation_information="Lowland puddle field.",
        soil_types="Clay,Loam",
        seasons="Kharif,Monsoon",
        locations="Kerala,Tamil Nadu",
        min_temp=Decimal("20.00"),
        max_temp=Decimal("38.00"),
        optimal_n=Decimal("80.00"),
    )
    disease = DiseaseInformation.objects.create(
        name="Rice blast",
        description="Fungal pathogen.",
        symptoms="Spindle shaped lesions.",
        treatment="Spray Tricyclazole.",
        prevention="Avoid excess nitrogen.",
        severity=DiseaseInformation.SEVERITY_HIGH,
    )

    assert str(crop) == "Rice"
    assert str(disease) == "Rice blast"
    assert CropInformation.matches("Clay", crop.soil_types) is True
    assert CropInformation.matches("Sandy", crop.soil_types) is False


def test_disease_detection_model_and_confidence(user):
    disease = DiseaseInformation.objects.create(
        name="Tomato early blight",
        description="Fungal spots.",
        treatment="Spray Mancozeb.",
        prevention="Crop rotation.",
    )
    detection = DiseaseDetection.objects.create(
        user=user,
        image="agriculture/disease-detections/sample.jpg",
        disease=disease,
        confidence=Decimal("0.9450"),
        treatment=disease.treatment,
        prevention=disease.prevention,
        status=DiseaseDetection.COMPLETE,
    )

    assert detection.confidence_percentage == 94.5
    assert "Tomato early blight" in str(detection)
    assert detection in user.disease_detections.all()


def test_crop_recommendation_model_and_json_fields(user):
    crop = CropInformation.objects.create(
        name="Wheat",
        description="Cool season crop.",
        cultivation_information="Sow in rows.",
        soil_types="Loam",
        seasons="Rabi",
    )
    rec = CropRecommendation.objects.create(
        user=user,
        soil_type="Loam",
        season="Rabi",
        location="Punjab",
        temperature=Decimal("18.00"),
        rainfall=Decimal("500.00"),
        ph=Decimal("6.50"),
        n=Decimal("100.00"),
        p=Decimal("50.00"),
        k=Decimal("40.00"),
        input_params={"soil_type": "Loam", "season": "Rabi"},
        recommended_crop=crop,
        recommended_crops_list=[{"crop_name": "Wheat", "percentage": 95}],
        explanation="Ideal loamy soil.",
    )

    assert rec.recommended_crop == crop
    assert rec.input_params["soil_type"] == "Loam"
    assert len(rec.recommended_crops_list) == 1
    assert "Wheat" in str(rec)


def test_market_price_model():
    crop = CropInformation.objects.create(
        name="Cotton",
        description="Fiber crop.",
        cultivation_information="Black soil.",
        soil_types="Black",
        seasons="Kharif",
    )
    price = MarketPrice.objects.create(
        crop=crop,
        market="Rajkot Yard",
        region="Gujarat",
        price=Decimal("7200.00"),
        unit="quintal",
        currency="INR",
        observed_at="2026-09-01T10:00:00Z",
        data_source=MarketPrice.SAMPLE,
    )

    assert price.get_data_source_display() == "Development sample"
    assert "7200.00" in str(price)
