"""Agricultural Knowledge Library Service."""

from typing import Dict, Tuple

from django.db.models import Q, QuerySet

from agrivision.agriculture.models import CropInformation
from agrivision.agriculture.models import DiseaseInformation


def search_agricultural_info(
    query: str = "",
    information_type: str = "",
) -> Tuple[QuerySet[CropInformation], QuerySet[DiseaseInformation]]:
    """Search crop encyclopedia and disease guides."""
    crops = CropInformation.objects.all()
    diseases = DiseaseInformation.objects.all()

    clean_q = query.strip()
    if clean_q:
        crops = crops.filter(
            Q(name__icontains=clean_q)
            | Q(description__icontains=clean_q)
            | Q(cultivation_information__icontains=clean_q)
            | Q(soil_types__icontains=clean_q)
        )
        diseases = diseases.filter(
            Q(name__icontains=clean_q)
            | Q(description__icontains=clean_q)
            | Q(treatment__icontains=clean_q)
            | Q(prevention__icontains=clean_q)
        )

    if information_type == "crop":
        diseases = DiseaseInformation.objects.none()
    elif information_type == "disease":
        crops = CropInformation.objects.none()

    return crops, diseases
