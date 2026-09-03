from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from agrivision.agriculture.forms import (
    DiseaseDetectionForm,
    SeasonRecommendationForm,
    SoilParamsRecommendationForm,
    SoilTypeRecommendationForm,
)


def create_test_image(format="PNG", content_type="image/png", size=(50, 50)):
    buf = BytesIO()
    Image.new("RGB", size, color="green").save(buf, format=format)
    return SimpleUploadedFile(f"test.{format.lower()}", buf.getvalue(), content_type=content_type)


def test_valid_image_form():
    form = DiseaseDetectionForm(files={"image": create_test_image()})
    assert form.is_valid()


def test_oversized_image_form():
    upload = create_test_image()
    upload.size = 5 * 1024 * 1024 + 10
    form = DiseaseDetectionForm(files={"image": upload})
    assert not form.is_valid()
    assert "5 MB" in str(form.errors)


def test_invalid_mime_type_form():
    upload = SimpleUploadedFile("test.txt", b"plain text", content_type="text/plain")
    form = DiseaseDetectionForm(files={"image": upload})
    assert not form.is_valid()


def test_soil_params_form_valid():
    form = SoilParamsRecommendationForm(data={
        "n": 80,
        "p": 40,
        "k": 40,
        "ph": 6.5,
        "rainfall": 1200,
        "temperature": 26.5,
        "soil_type": "Clay",
        "season": "Kharif",
        "location": "Kerala",
    })
    assert form.is_valid()


def test_soil_params_form_out_of_range():
    form = SoilParamsRecommendationForm(data={
        "ph": 14.5,  # Max is 11.0
        "n": 500,    # Max is 300
    })
    assert not form.is_valid()
    assert "ph" in form.errors
    assert "n" in form.errors


def test_season_recommendation_form():
    form = SeasonRecommendationForm(data={"season": "Kharif", "location": "Kerala"})
    assert form.is_valid()


def test_soil_type_recommendation_form():
    form = SoilTypeRecommendationForm(data={"soil_type": "Clay", "location": "Kerala"})
    assert form.is_valid()
