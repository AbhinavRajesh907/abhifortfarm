from http import HTTPStatus
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
import pytest

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


def test_views_require_login(client):
    urls = [
        reverse("agriculture:smart_assistant"),
        reverse("agriculture:chatbot"),
        reverse("agriculture:disease_detection"),
        reverse("agriculture:disease_history"),
        reverse("agriculture:crop_recommendation"),
        reverse("agriculture:crop_history"),
        reverse("agriculture:market_prices"),
        reverse("agriculture:agriculture_info"),
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == HTTPStatus.FOUND
        assert "/login/" in response.url


def test_authenticated_views_load(client, user):
    client.force_login(user)
    urls = [
        reverse("agriculture:smart_assistant"),
        reverse("agriculture:chatbot"),
        reverse("agriculture:disease_detection"),
        reverse("agriculture:disease_history"),
        reverse("agriculture:crop_recommendation"),
        reverse("agriculture:crop_history"),
        reverse("agriculture:market_prices"),
        reverse("agriculture:agriculture_info"),
    ]
    for url in urls:
        response = client.get(url, follow=True)
        assert response.status_code == HTTPStatus.OK



@patch("agrivision.agriculture.services.disease_detection.MLServiceClient.predict")
def test_disease_detection_post_and_result(mock_predict, client, user):
    mock_predict.return_value = {
        "status": "success",
        "disease": "Tomato early blight",
        "confidence": 0.945,
    }
    DiseaseInformation.objects.create(
        name="Tomato early blight",
        description="Fungal blight.",
        treatment="Spray copper fungicide.",
        prevention="Crop rotation.",
    )

    client.force_login(user)
    response = client.post(
        reverse("agriculture:disease_detection"),
        {"image": create_test_image()},
    )
    assert response.status_code == HTTPStatus.FOUND

    detection = DiseaseDetection.objects.filter(user=user).first()
    assert detection is not None
    assert detection.disease.name == "Tomato early blight"

    # View result page
    result_resp = client.get(reverse("agriculture:disease_result", kwargs={"pk": detection.pk}))
    assert result_resp.status_code == HTTPStatus.OK
    assert "Tomato early blight" in result_resp.content.decode()


def test_crop_recommendation_post(client, user):
    CropInformation.objects.create(
        name="Rice",
        description="Paddy crop.",
        cultivation_information="Puddle field.",
        soil_types="Clay",
        seasons="Kharif",
        locations="Kerala",
    )
    client.force_login(user)
    response = client.post(
        reverse("agriculture:crop_recommendation"),
        {
            "form_type": "params",
            "soil_type": "Clay",
            "season": "Kharif",
            "location": "Kerala",
            "temperature": 28,
            "rainfall": 1500,
        },
    )
    assert response.status_code == HTTPStatus.OK
    assert "Rice" in response.content.decode()

    rec = CropRecommendation.objects.filter(user=user).first()
    assert rec is not None
    assert rec.recommended_crop.name == "Rice"
