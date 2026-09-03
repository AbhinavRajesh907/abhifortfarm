from io import StringIO

import pytest
from django.core.management import call_command

from agrivision.agriculture.models import (
    CropInformation,
    CropRecommendation,
    DiseaseInformation,
    MarketPrice,
)

pytestmark = pytest.mark.django_db


def test_seed_agriculture_demo_is_repeatable(user):
    output = StringIO()

    call_command("seed_agriculture_demo", email=user.email, stdout=output)
    call_command("seed_agriculture_demo", email=user.email, stdout=output)

    # Verify idempotency and correct counts (6 crops, 6 diseases, 12 price entries)
    assert CropInformation.objects.count() == 6
    assert DiseaseInformation.objects.count() == 6
    assert MarketPrice.objects.count() == 12
    assert CropRecommendation.objects.filter(user=user).count() == 1
    assert "AI & Agriculture demo data seeded successfully" in output.getvalue()


def test_seed_agriculture_demo_without_email():
    output = StringIO()
    call_command("seed_agriculture_demo", stdout=output)
    # Should create crop and disease data but no user history
    assert CropInformation.objects.count() == 6
    assert DiseaseInformation.objects.count() == 6
