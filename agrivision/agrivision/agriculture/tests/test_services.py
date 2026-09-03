from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from agrivision.agriculture.models import (
    CropInformation,
    DiseaseDetection,
    DiseaseInformation,
    MarketPrice,
)
from agrivision.agriculture.services.agri_info import search_agricultural_info
from agrivision.agriculture.services.crop_recommendation import (
    recommend_by_season,
    recommend_by_soil_parameters,
    recommend_by_soil_type,
    save_crop_recommendation_history,
)
from agrivision.agriculture.services.disease_detection import (
    DiseaseDetectionService,
    MLServiceClient,
)
from agrivision.agriculture.services.market_price import get_market_prices

pytestmark = pytest.mark.django_db


def test_crop_recommendation_soil_parameters():
    CropInformation.objects.create(
        name="Rice",
        description="Paddy crop.",
        cultivation_information="Lowland puddle field.",
        soil_types="Clay,Loam",
        seasons="Kharif,Monsoon",
        locations="Kerala,Tamil Nadu",
        min_temp=Decimal("20.00"),
        max_temp=Decimal("38.00"),
        min_ph=Decimal("5.00"),
        max_ph=Decimal("7.50"),
        min_rainfall=Decimal("1000.00"),
        max_rainfall=Decimal("2500.00"),
        optimal_n=Decimal("80.00"),
        optimal_p=Decimal("40.00"),
        optimal_k=Decimal("40.00"),
    )
    CropInformation.objects.create(
        name="Wheat",
        description="Cool season rabi crop.",
        cultivation_information="Loam soil.",
        soil_types="Loam",
        seasons="Rabi,Winter",
        locations="Punjab",
        min_temp=Decimal("10.00"),
        max_temp=Decimal("25.00"),
        min_ph=Decimal("6.00"),
        max_ph=Decimal("7.80"),
        min_rainfall=Decimal("350.00"),
        max_rainfall=Decimal("800.00"),
        optimal_n=Decimal("120.00"),
        optimal_p=Decimal("60.00"),
        optimal_k=Decimal("40.00"),
    )

    # Test parameter matching favorable to Rice
    result = recommend_by_soil_parameters(
        n=80, p=40, k=40, ph=6.0, rainfall=1500, temperature=28,
        soil_type="Clay", season="Kharif", location="Kerala",
    )

    assert result.primary_crop is not None
    assert result.primary_crop.name == "Rice"
    assert len(result.ranked_crops) >= 1
    assert result.ranked_crops[0].suitability_percentage >= 80


def test_crop_recommendation_season():
    CropInformation.objects.create(
        name="Wheat",
        description="Wheat.",
        cultivation_information="Details.",
        soil_types="Loam",
        seasons="Rabi,Winter",
        locations="Punjab",
    )
    result = recommend_by_season(season="Rabi", location="Punjab")

    assert result.primary_crop is not None
    assert result.primary_crop.name == "Wheat"
    assert result.total_matches >= 1


def test_crop_recommendation_soil_type():
    CropInformation.objects.create(
        name="Cotton",
        description="Cotton.",
        cultivation_information="Details.",
        soil_types="Black,Loam",
        seasons="Kharif",
    )
    result = recommend_by_soil_type(soil_type="Black", location="")

    assert result.primary_crop is not None
    assert result.primary_crop.name == "Cotton"


def test_save_crop_recommendation_history(user):
    crop = CropInformation.objects.create(
        name="Tomato",
        description="Tomato.",
        cultivation_information="Details.",
        soil_types="Loam",
        seasons="Winter",
    )
    result = recommend_by_soil_parameters(soil_type="Loam", season="Winter")
    rec = save_crop_recommendation_history(user, result, raw_params={"soil_type": "Loam", "season": "Winter"})

    assert rec.user == user
    assert rec.recommended_crop == crop
    assert rec.soil_type == "Loam"


def test_disease_detection_service_with_mocked_client(user):
    DiseaseInformation.objects.create(
        name="Tomato early blight",
        description="Alternaria solani infection.",
        treatment="Spray Mancozeb at 2.5g/L.",
        prevention="Crop rotation and remove infected foliage.",
    )

    mock_client = MagicMock(spec=MLServiceClient)
    mock_client.predict.return_value = {
        "status": "success",
        "disease": "Tomato early blight",
        "confidence": 0.932,
    }

    service = DiseaseDetectionService(client=mock_client)
    sample_img = SimpleUploadedFile("leaf.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20, content_type="image/jpeg")

    detection = service.process_and_record(user, sample_img)

    assert detection.status == DiseaseDetection.COMPLETE
    assert detection.disease.name == "Tomato early blight"
    assert float(detection.confidence) == 0.932
    assert "Mancozeb" in detection.treatment


def test_disease_detection_service_when_microservice_offline(user):
    mock_client = MagicMock(spec=MLServiceClient)
    mock_client.predict.return_value = {
        "status": "unreachable",
        "disease": None,
        "confidence": None,
        "error": "Connection refused",
    }

    service = DiseaseDetectionService(client=mock_client)
    sample_img = SimpleUploadedFile("leaf.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 20, content_type="image/jpeg")

    detection = service.process_and_record(user, sample_img)

    assert detection.status == DiseaseDetection.UNAVAILABLE
    assert detection.disease is None
    assert "offline" in detection.treatment.lower()


def test_search_agricultural_info():
    CropInformation.objects.create(
        name="Rice",
        description="Cereal grain.",
        cultivation_information="Puddled soil.",
        soil_types="Clay",
        seasons="Kharif",
    )
    DiseaseInformation.objects.create(
        name="Rice blast",
        description="Fungal rot.",
        treatment="Fungicide.",
        prevention="Resistant variety.",
    )

    crops, diseases = search_agricultural_info(query="Rice")
    assert crops.count() == 1
    assert diseases.count() == 1

    crops_only, _ = search_agricultural_info(query="Rice", information_type="crop")
    assert crops_only.count() == 1
