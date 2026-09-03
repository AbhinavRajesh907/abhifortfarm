from http import HTTPStatus
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
import pytest
import json

from agrivision.agriculture.models import (
    CropInformation,
    CropRecommendation,
    DiseaseDetection,
    DiseaseInformation,
    MarketPrice,
)

pytestmark = pytest.mark.django_db


def create_test_image():
    buf = BytesIO()
    Image.new("RGB", (60, 60), color="green").save(buf, format="JPEG")
    return SimpleUploadedFile("leaf.jpg", buf.getvalue(), content_type="image/jpeg")


def create_crop(name="Rice", soil_types="Clay", seasons="Kharif", locations="Kerala"):
    return CropInformation.objects.create(
        name=name,
        description=f"{name} crop.",
        cultivation_information=f"{name} cultivation details.",
        soil_types=soil_types,
        seasons=seasons,
        locations=locations,
    )


# ---- Disease Detection API ----

def test_api_disease_detection_upload_requires_auth(client):
    response = client.post(
        reverse("agriculture:api_disease_detection_upload"),
        {"image": create_test_image()},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED


@patch("agrivision.agriculture.services.disease_detection.MLServiceClient.predict")
def test_api_disease_detection_upload_success(mock_predict, client, user):
    mock_predict.return_value = {
        "status": "success",
        "disease": "Rice blast",
        "confidence": 0.91,
    }
    DiseaseInformation.objects.create(
        name="Rice blast",
        description="Fungal blast.",
        treatment="Spray Tricyclazole.",
        prevention="Resistant varieties.",
    )

    client.force_login(user)
    response = client.post(
        reverse("agriculture:api_disease_detection_upload"),
        {"image": create_test_image()},
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["detected_disease"] == "Rice blast"
    assert data["data"]["confidence_score"] == 0.91


def test_api_disease_detection_history(client, user):
    client.force_login(user)
    response = client.get(reverse("agriculture:api_disease_detection_history"))
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "detections" in data["data"]
    assert "total_count" in data["data"]


# ---- Crop Recommendations API ----

def test_api_recommend_crop_post(client, user):
    create_crop("Rice")
    client.force_login(user)
    response = client.post(
        reverse("agriculture:api_recommend_crop"),
        data=json.dumps({
            "soil_type": "Clay",
            "season": "Kharif",
            "location": "Kerala",
            "temperature": 28,
            "rainfall": 1500,
            "ph": 6.0,
            "n": 80,
            "p": 40,
            "k": 40,
        }),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["primary_crop"] is not None


def test_api_recommend_season(client, user):
    create_crop("Wheat", soil_types="Loam", seasons="Rabi")
    client.force_login(user)
    response = client.post(
        reverse("agriculture:api_recommend_season"),
        data=json.dumps({"season": "Rabi"}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["data"]["season"] == "Rabi"


def test_api_recommend_season_missing_field(client, user):
    client.force_login(user)
    response = client.post(
        reverse("agriculture:api_recommend_season"),
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_api_recommend_soil(client, user):
    create_crop("Cotton", soil_types="Black", seasons="Kharif")
    client.force_login(user)
    response = client.post(
        reverse("agriculture:api_recommend_soil"),
        data=json.dumps({"soil_type": "Black"}),
        content_type="application/json",
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["data"]["soil_type"] == "Black"


# ---- Market Prices & Agri Info API ----

def test_api_market_prices(client, user):
    client.force_login(user)
    response = client.get(reverse("agriculture:api_market_prices"))
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "market_prices" in data["data"]


def test_api_agri_info(client, user):
    create_crop("Rice")
    DiseaseInformation.objects.create(
        name="Rice blast",
        description="Fungal blast.",
        treatment="Tricyclazole.",
        prevention="Rotation.",
    )
    client.force_login(user)
    response = client.get(reverse("agriculture:api_agri_info") + "?query=Rice")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data["data"]["crops"]) >= 1
    assert len(data["data"]["diseases"]) >= 1


def test_api_crop_recommendations_history(client, user):
    client.force_login(user)
    response = client.get(reverse("agriculture:api_crop_recommendations_history"))
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert "recommendations" in data["data"]
