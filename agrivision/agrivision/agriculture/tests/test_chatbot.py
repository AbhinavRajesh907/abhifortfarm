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
from agrivision.agriculture.services.chatbot import AgriChatbotService

pytestmark = pytest.mark.django_db


def create_test_image():
    buf = BytesIO()
    Image.new("RGB", (60, 60), color="green").save(buf, format="JPEG")
    return SimpleUploadedFile("leaf.jpg", buf.getvalue(), content_type="image/jpeg")


def test_chatbot_service_greeting(user):
    service = AgriChatbotService()
    res = service.process_message(user, message="Hello, who are you?")
    assert res.intent == "greeting"
    assert "AgriBot" in res.reply_text
    assert len(res.quick_replies) > 0


@patch("agrivision.agriculture.services.disease_detection.MLServiceClient.predict")
def test_chatbot_service_image_upload(mock_predict, user):
    mock_predict.return_value = {
        "status": "success",
        "disease": "Tomato early blight",
        "confidence": 0.92,
    }
    DiseaseInformation.objects.create(
        name="Tomato early blight",
        description="Fungal blight spots.",
        symptoms="Dark concentric leaf spots.",
        treatment="Apply copper fungicide.",
        prevention="Crop rotation and spacing.",
        severity="medium",
    )

    service = AgriChatbotService()
    img = create_test_image()
    res = service.process_message(user, message="", image_file=img)

    assert res.intent == "disease_detection"
    assert "Tomato early blight" in res.reply_text
    assert res.created_record_id is not None

    detection = DiseaseDetection.objects.get(pk=res.created_record_id)
    assert detection.user == user
    assert detection.disease.name == "Tomato early blight"


def test_chatbot_service_crop_recommendation(user):
    CropInformation.objects.create(
        name="Rice",
        description="Paddy crop",
        cultivation_information="Sow in waterlogged fields",
        soil_types="Clay, Loam",
        seasons="Kharif",
    )

    service = AgriChatbotService()
    res = service.process_message(user, message="Recommend crops for Kharif season in Clay soil")

    assert res.intent == "crop_recommendation"
    assert "Rice" in res.reply_text
    assert res.created_record_id is not None

    rec = CropRecommendation.objects.get(pk=res.created_record_id)
    assert rec.user == user


def test_chatbot_service_market_price():
    crop = CropInformation.objects.create(
        name="Wheat",
        description="Grain crop",
        cultivation_information="Irrigated wheat",
        soil_types="Loam",
        seasons="Rabi",
    )
    MarketPrice.objects.create(
        crop=crop,
        market="Punjab Mandi",
        region="Punjab",
        price=2400.00,
        unit="quintal",
        observed_at="2026-09-11 10:00:00+00:00",
    )

    service = AgriChatbotService()
    res = service.process_message(None, message="What is the market price of Wheat?")

    assert res.intent == "market_price"
    assert "Wheat" in res.reply_text
    assert "2400.00" in res.reply_text


def test_api_agri_chatbot_endpoint(client, user):
    client.force_login(user)
    url = reverse("agriculture:api_agri_chatbot")

    # Text payload
    response = client.post(
        url,
        data={"message": "Recommend crops for Kharif season"},
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["intent"] == "crop_recommendation"
    assert len(data["data"]["quick_replies"]) > 0


def test_chatbot_service_non_plant_image_rejection(user):
    # Create synthetic indoor dining room image (beige background + brown table)
    import numpy as np
    room_arr = np.zeros((100, 100, 3), dtype=np.uint8)
    room_arr[:70, :] = [230, 220, 205]  # Beige cream wall
    room_arr[70:, :] = [140, 90, 50]    # Wooden table
    room_img = Image.fromarray(room_arr)

    buf = BytesIO()
    room_img.save(buf, format="JPEG")
    uploaded_file = SimpleUploadedFile("room.jpg", buf.getvalue(), content_type="image/jpeg")

    service = AgriChatbotService()
    res = service.process_message(user, message="", image_file=uploaded_file)

    assert res.intent == "disease_detection_error"
    assert "Non-Plant" in res.reply_text or "Indoor Room" in res.reply_text
    assert res.created_record_id is None

