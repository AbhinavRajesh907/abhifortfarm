"""Market Price service for agricultural commodities."""

from datetime import timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import QuerySet
from django.utils import timezone

from agrivision.agriculture.models import CropInformation
from agrivision.agriculture.models import MarketPrice


def get_market_prices(
    *,
    crop_name: str = "",
    market: str = "",
    region: str = "",
) -> QuerySet[MarketPrice]:
    """Retrieve and filter market prices with related crop data."""
    prices = MarketPrice.objects.select_related("crop").all()
    if crop_name:
        prices = prices.filter(crop__name__icontains=crop_name.strip())
    if market:
        prices = prices.filter(market__icontains=market.strip())
    if region:
        prices = prices.filter(region__icontains=region.strip())
    return prices


def development_sample_prices() -> list[MarketPrice]:
    """Return fallback development sample prices."""
    now = timezone.now()
    samples = []
    sample_data = [
        ("Rice", Decimal("2500.00"), "Kochi Wholesale APMC", "Kerala"),
        ("Wheat", Decimal("2250.00"), "Azadpur Mandi", "Delhi"),
        ("Tomato", Decimal("1850.00"), "Kolar Market", "Karnataka"),
        ("Maize", Decimal("2100.00"), "Hubballi Market", "Karnataka"),
        ("Potato", Decimal("1600.00"), "Agra Mandi", "Uttar Pradesh"),
        ("Cotton", Decimal("7200.00"), "Rajkot Yard", "Gujarat"),
    ]
    for name, price, market, region in sample_data:
        crop = CropInformation.objects.filter(name__iexact=name).first()
        if crop:
            samples.append(
                MarketPrice(
                    crop=crop,
                    market=market,
                    region=region,
                    price=price,
                    unit="quintal",
                    currency="INR",
                    observed_at=now - timedelta(days=1),
                    data_source=MarketPrice.SAMPLE,
                )
            )
    return samples
