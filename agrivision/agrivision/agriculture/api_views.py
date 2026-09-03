"""REST API Views for AI & Agriculture Module.

Provides headless / mobile JSON endpoints matching standard API specifications:
- POST /agriculture/api/disease-detection/upload/
- GET  /agriculture/api/disease-detection/history/
- POST /agriculture/api/recommendations/crop/
- POST /agriculture/api/recommendations/season/
- POST /agriculture/api/recommendations/soil/
- GET  /agriculture/api/market-prices/
- GET  /agriculture/api/agri-info/
- GET  /agriculture/api/crop-recommendations/history/
"""

import json
import logging
from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from agrivision.agriculture.forms import DiseaseDetectionForm
from agrivision.agriculture.models import CropRecommendation
from agrivision.agriculture.models import DiseaseDetection
from agrivision.agriculture.services.agri_info import search_agricultural_info
from agrivision.agriculture.services.crop_recommendation import (
    recommend_by_season,
    recommend_by_soil_parameters,
    recommend_by_soil_type,
    save_crop_recommendation_history,
)
from agrivision.agriculture.services.disease_detection import DiseaseDetectionService
from agrivision.agriculture.services.market_price import get_market_prices

logger = logging.getLogger(__name__)


def api_error_response(message: str, status_code: int = 400, details: Any = None) -> JsonResponse:
    """Standardized API error response format."""
    payload: Dict[str, Any] = {"status": "error", "message": message}
    if details:
        payload["details"] = details
    return JsonResponse(payload, status=status_code)


def api_success_response(data: Any, message: str = "Success", status_code: int = 200) -> JsonResponse:
    """Standardized API success response format."""
    return JsonResponse({"status": "success", "message": message, "data": data}, status=status_code)


@require_POST
def api_disease_detection_upload(request) -> JsonResponse:
    """Upload plant image for AI disease diagnosis.

    Accepts multipart/form-data with 'image' field.
    """
    if not request.user.is_authenticated:
        return api_error_response("Authentication required. Please log in.", status_code=401)

    form = DiseaseDetectionForm(request.POST, request.FILES)
    if not form.is_valid():
        return api_error_response("Invalid image upload.", details=form.errors.get_json_data())

    try:
        service = DiseaseDetectionService()
        detection = service.process_and_record(request.user, form.cleaned_data["image"])

        data = {
            "id": detection.id,
            "image_url": request.build_absolute_uri(detection.image.url) if detection.image else None,
            "detected_disease": detection.disease.name if detection.disease else None,
            "disease_description": detection.disease.description if detection.disease else None,
            "confidence_score": float(detection.confidence) if detection.confidence is not None else None,
            "confidence_percentage": detection.confidence_percentage,
            "treatment_suggestion": detection.treatment,
            "preventive_measures": detection.prevention,
            "status": detection.status,
            "created_at": detection.created_at.isoformat(),
        }
        return api_success_response(data, message="Disease diagnosis completed successfully.", status_code=201)
    except Exception as exc:
        logger.exception(f"API Disease detection error: {exc}")
        return api_error_response(f"An error occurred during image processing: {str(exc)}", status_code=500)


@require_GET
def api_disease_detection_history(request) -> JsonResponse:
    """Retrieve user's plant disease detection history."""
    if not request.user.is_authenticated:
        return api_error_response("Authentication required.", status_code=401)

    detections = DiseaseDetection.objects.filter(user=request.user).select_related("disease")
    history = [
        {
            "id": d.id,
            "image_url": request.build_absolute_uri(d.image.url) if d.image else None,
            "detected_disease": d.disease.name if d.disease else "Unclassified",
            "confidence_score": float(d.confidence) if d.confidence is not None else None,
            "confidence_percentage": d.confidence_percentage,
            "treatment": d.treatment,
            "prevention": d.prevention,
            "status": d.status,
            "created_at": d.created_at.isoformat(),
        }
        for d in detections
    ]
    return api_success_response({"detections": history, "total_count": len(history)})


@require_POST
def api_recommend_crop(request) -> JsonResponse:
    """Recommend crops based on soil and climatic parameters.

    Accepts JSON body or POST form data:
    { "n": 80, "p": 40, "k": 40, "ph": 6.5, "rainfall": 1200, "temperature": 26, "soil_type": "Clay", "season": "Kharif", "location": "Kerala" }
    """
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body)
        else:
            payload = request.POST.dict()
    except Exception:
        return api_error_response("Invalid JSON payload.")

    n = float(payload["n"]) if payload.get("n") not in (None, "") else None
    p = float(payload["p"]) if payload.get("p") not in (None, "") else None
    k = float(payload["k"]) if payload.get("k") not in (None, "") else None
    ph = float(payload["ph"]) if payload.get("ph") not in (None, "") else None
    rainfall = float(payload["rainfall"]) if payload.get("rainfall") not in (None, "") else None
    temperature = float(payload["temperature"]) if payload.get("temperature") not in (None, "") else None
    soil_type = str(payload.get("soil_type") or "").strip()
    season = str(payload.get("season") or "").strip()
    location = str(payload.get("location") or "").strip()

    result = recommend_by_soil_parameters(
        n=n, p=p, k=k, ph=ph, rainfall=rainfall, temperature=temperature,
        soil_type=soil_type, season=season, location=location,
    )

    # Save to history if user is authenticated
    history_id = None
    if request.user.is_authenticated:
        history_record = save_crop_recommendation_history(request.user, result, raw_params=payload)
        history_id = history_record.id

    ranked_data = [
        {
            "crop_id": r.crop.id,
            "crop_name": r.crop.name,
            "suitability_percentage": r.suitability_percentage,
            "score": r.score,
            "matched_factors": r.matched_factors,
            "explanation": r.explanation,
            "cultivation_information": r.crop.cultivation_information,
            "marketplace_products": [
                {"id": prod.id, "name": prod.name, "price": float(prod.price), "category": prod.category.name}
                for prod in r.marketplace_products
            ],
        }
        for r in result.ranked_crops
    ]

    response_data = {
        "history_id": history_id,
        "recommendation_type": result.recommendation_type,
        "primary_crop": result.primary_crop.name if result.primary_crop else None,
        "explanation": result.explanation,
        "ranked_crops": ranked_data,
        "total_matches": result.total_matches,
    }
    return api_success_response(response_data)


@require_POST
def api_recommend_season(request) -> JsonResponse:
    """Recommend crops based on agricultural season."""
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body)
        else:
            payload = request.POST.dict()
    except Exception:
        return api_error_response("Invalid JSON payload.")

    season = str(payload.get("season") or "").strip()
    if not season:
        return api_error_response("Field 'season' is required (e.g. Kharif, Rabi, Summer, Monsoon, Winter).")

    location = str(payload.get("location") or "").strip()
    result = recommend_by_season(season=season, location=location)

    history_id = None
    if request.user.is_authenticated:
        history_record = save_crop_recommendation_history(request.user, result, raw_params=payload)
        history_id = history_record.id

    ranked_data = [
        {
            "crop_id": r.crop.id,
            "crop_name": r.crop.name,
            "suitability_percentage": r.suitability_percentage,
            "matched_factors": r.matched_factors,
            "explanation": r.explanation,
            "marketplace_products": [
                {"id": prod.id, "name": prod.name, "price": float(prod.price), "category": prod.category.name}
                for prod in r.marketplace_products
            ],
        }
        for r in result.ranked_crops
    ]

    return api_success_response({
        "history_id": history_id,
        "season": season,
        "primary_crop": result.primary_crop.name if result.primary_crop else None,
        "explanation": result.explanation,
        "ranked_crops": ranked_data,
    })


@require_POST
def api_recommend_soil(request) -> JsonResponse:
    """Recommend crops based on soil type and link to marketplace products."""
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body)
        else:
            payload = request.POST.dict()
    except Exception:
        return api_error_response("Invalid JSON payload.")

    soil_type = str(payload.get("soil_type") or "").strip()
    if not soil_type:
        return api_error_response("Field 'soil_type' is required (e.g. Clay, Loam, Sandy loam, Black).")

    location = str(payload.get("location") or "").strip()
    result = recommend_by_soil_type(soil_type=soil_type, location=location)

    history_id = None
    if request.user.is_authenticated:
        history_record = save_crop_recommendation_history(request.user, result, raw_params=payload)
        history_id = history_record.id

    ranked_data = [
        {
            "crop_id": r.crop.id,
            "crop_name": r.crop.name,
            "suitability_percentage": r.suitability_percentage,
            "matched_factors": r.matched_factors,
            "explanation": r.explanation,
            "marketplace_products": [
                {"id": prod.id, "name": prod.name, "price": float(prod.price), "category": prod.category.name}
                for prod in r.marketplace_products
            ],
        }
        for r in result.ranked_crops
    ]

    return api_success_response({
        "history_id": history_id,
        "soil_type": soil_type,
        "primary_crop": result.primary_crop.name if result.primary_crop else None,
        "explanation": result.explanation,
        "ranked_crops": ranked_data,
    })


@require_GET
def api_market_prices(request) -> JsonResponse:
    """Get market prices with optional crop, market, or region filters."""
    crop_name = request.GET.get("crop", "").strip()
    market = request.GET.get("market", "").strip()
    region = request.GET.get("region", "").strip()

    prices = get_market_prices(crop_name=crop_name, market=market, region=region)
    data = [
        {
            "id": p.id,
            "crop_name": p.crop.name,
            "market": p.market,
            "region": p.region,
            "price": float(p.price),
            "unit": p.unit,
            "currency": p.currency,
            "observed_at": p.observed_at.isoformat(),
            "data_source": p.data_source,
        }
        for p in prices
    ]
    return api_success_response({"market_prices": data, "total_count": len(data)})


@require_GET
def api_agri_info(request) -> JsonResponse:
    """Get crop and plant disease encyclopedia information."""
    query = request.GET.get("query", "").strip()
    info_type = request.GET.get("information_type", "").strip()

    crops, diseases = search_agricultural_info(query=query, information_type=info_type)
    crops_data = [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "cultivation_information": c.cultivation_information,
            "soil_types": c.soil_types,
            "seasons": c.seasons,
            "locations": c.locations,
        }
        for c in crops
    ]
    diseases_data = [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "symptoms": d.symptoms,
            "treatment": d.treatment,
            "prevention": d.prevention,
            "severity": d.severity,
        }
        for d in diseases
    ]
    return api_success_response({"crops": crops_data, "diseases": diseases_data})


@require_GET
def api_crop_recommendations_history(request) -> JsonResponse:
    """Retrieve user's crop recommendation history."""
    if not request.user.is_authenticated:
        return api_error_response("Authentication required.", status_code=401)

    records = CropRecommendation.objects.filter(user=request.user).select_related("recommended_crop")
    data = [
        {
            "id": rec.id,
            "recommended_crop": rec.recommended_crop.name if rec.recommended_crop else "None",
            "soil_type": rec.soil_type,
            "season": rec.season,
            "location": rec.location,
            "temperature": float(rec.temperature) if rec.temperature is not None else None,
            "rainfall": float(rec.rainfall) if rec.rainfall is not None else None,
            "ph": float(rec.ph) if rec.ph is not None else None,
            "n": float(rec.n) if rec.n is not None else None,
            "p": float(rec.p) if rec.p is not None else None,
            "k": float(rec.k) if rec.k is not None else None,
            "explanation": rec.explanation,
            "ranked_crops": rec.recommended_crops_list,
            "created_at": rec.created_at.isoformat(),
        }
        for rec in records
    ]
    return api_success_response({"recommendations": data, "total_count": len(data)})
