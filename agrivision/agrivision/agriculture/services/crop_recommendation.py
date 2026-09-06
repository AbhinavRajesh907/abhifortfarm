"""Agronomic Crop & Farming Recommendation Service.

Implements multi-criteria recommendation algorithms based on:
1. Soil parameters (N, P, K, pH, rainfall, temperature)
2. Seasonal suitability
3. Soil type matching + Marketplace seed & plant product linking
"""

from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional

from django.apps import apps

from agrivision.agriculture.models import CropInformation
from agrivision.agriculture.models import CropRecommendation

logger = logging.getLogger(__name__)


@dataclass
class RankedCropResult:
    crop: CropInformation
    score: float
    suitability_percentage: int
    matched_factors: List[str]
    explanation: str
    marketplace_products: List[Any] = field(default_factory=list)


@dataclass
class CropRecommendationResult:
    primary_crop: Optional[CropInformation]
    ranked_crops: List[RankedCropResult]
    explanation: str
    recommendation_type: str
    input_summary: Dict[str, Any]
    total_matches: int


def get_linked_marketplace_products(crop_name: str, limit: int = 4) -> List[Any]:
    """Retrieve marketplace seed and plant products matching the given crop name."""
    try:
        if apps.is_installed("agrivision.marketplace"):
            Product = apps.get_model("marketplace", "Product")
            # Query products whose name contains the crop name (e.g. 'Tomato Seeds', 'Rice Plants')
            products = Product.objects.filter(
                is_active=True,
                name__icontains=crop_name,
            ).select_related("category")[:limit]
            return list(products)
    except Exception as exc:
        logger.debug(f"Could not retrieve marketplace products for {crop_name}: {exc}")
    return []


def recommend_by_soil_parameters(
    *,
    n: Optional[float] = None,
    p: Optional[float] = None,
    k: Optional[float] = None,
    ph: Optional[float] = None,
    rainfall: Optional[float] = None,
    temperature: Optional[float] = None,
    soil_type: str = "",
    season: str = "",
    location: str = "",
) -> CropRecommendationResult:
    """Recommend crops based on comprehensive soil chemical, climatic, and seasonal parameters."""
    crops = list(CropInformation.objects.all())
    if not crops:
        return CropRecommendationResult(
            primary_crop=None,
            ranked_crops=[],
            explanation="No crop encyclopedia records found in the database. Please seed agricultural data.",
            recommendation_type="soil_parameters",
            input_summary={
                "n": n, "p": p, "k": k, "ph": ph, "rainfall": rainfall,
                "temperature": temperature, "soil_type": soil_type, "season": season, "location": location,
            },
            total_matches=0,
        )

    scored_crops: List[RankedCropResult] = []

    for crop in crops:
        score = 0.0
        max_possible_score = 0.0
        matched_factors = []
        notes = []

        # 1. Temperature suitability (weight: 20)
        if temperature is not None:
            max_possible_score += 20.0
            t_val = float(temperature)
            min_t = float(crop.min_temp) if crop.min_temp is not None else 15.0
            max_t = float(crop.max_temp) if crop.max_temp is not None else 35.0
            if min_t <= t_val <= max_t:
                score += 20.0
                matched_factors.append("Optimal Temperature")
                notes.append(f"Temperature {t_val}°C is well within optimal range ({min_t}-{max_t}°C)")
            elif (min_t - 5.0) <= t_val <= (max_t + 5.0):
                score += 10.0
                notes.append(f"Temperature {t_val}°C is acceptable with irrigation adjustments")
            else:
                notes.append(f"Temperature {t_val}°C is outside ideal range ({min_t}-{max_t}°C)")

        # 2. pH suitability (weight: 20)
        if ph is not None:
            max_possible_score += 20.0
            ph_val = float(ph)
            min_ph = float(crop.min_ph) if crop.min_ph is not None else 5.5
            max_ph = float(crop.max_ph) if crop.max_ph is not None else 7.5
            if min_ph <= ph_val <= max_ph:
                score += 20.0
                matched_factors.append("Optimal pH")
                notes.append(f"Soil pH {ph_val} is optimal (tolerance: {min_ph}-{max_ph})")
            elif (min_ph - 0.8) <= ph_val <= (max_ph + 0.8):
                score += 10.0
                notes.append(f"Soil pH {ph_val} is moderately suitable (lime/sulfur correction suggested)")
            else:
                notes.append(f"Soil pH {ph_val} may require soil conditioning")

        # 3. Rainfall suitability (weight: 20)
        if rainfall is not None:
            max_possible_score += 20.0
            rf_val = float(rainfall)
            min_rf = float(crop.min_rainfall) if crop.min_rainfall is not None else 400.0
            max_rf = float(crop.max_rainfall) if crop.max_rainfall is not None else 1800.0
            if min_rf <= rf_val <= max_rf:
                score += 20.0
                matched_factors.append("Adequate Rainfall")
                notes.append(f"Rainfall {rf_val} mm matches crop water requirement ({min_rf}-{max_rf} mm)")
            elif rf_val < min_rf:
                score += 8.0
                notes.append(f"Rainfall {rf_val} mm is low; supplemental drip irrigation recommended")
            else:
                score += 10.0
                notes.append(f"Rainfall {rf_val} mm is high; ensure proper soil drainage")

        # 4. NPK nutrient profile (weight: 20)
        npk_evaluated = False
        npk_subscore = 0.0
        if n is not None and crop.optimal_n is not None:
            npk_evaluated = True
            diff_n = abs(float(n) - float(crop.optimal_n))
            if diff_n <= 30:
                npk_subscore += 7.0
            elif diff_n <= 60:
                npk_subscore += 4.0
        if p is not None and crop.optimal_p is not None:
            npk_evaluated = True
            diff_p = abs(float(p) - float(crop.optimal_p))
            if diff_p <= 20:
                npk_subscore += 7.0
            elif diff_p <= 40:
                npk_subscore += 4.0
        if k is not None and crop.optimal_k is not None:
            npk_evaluated = True
            diff_k = abs(float(k) - float(crop.optimal_k))
            if diff_k <= 20:
                npk_subscore += 6.0
            elif diff_k <= 40:
                npk_subscore += 3.0

        if npk_evaluated:
            max_possible_score += 20.0
            score += npk_subscore
            if npk_subscore >= 14:
                matched_factors.append("Balanced NPK")
                notes.append("Soil N-P-K nutrient profile aligns closely with optimal crop requirements")

        # 5. Soil type & Season text matching (weight: 10 each)
        if soil_type:
            max_possible_score += 10.0
            if CropInformation.matches(soil_type, crop.soil_types):
                score += 10.0
                matched_factors.append("Matching Soil Type")
                notes.append(f"Soil type '{soil_type}' matches {crop.soil_types}")

        if season:
            max_possible_score += 10.0
            if CropInformation.matches(season, crop.seasons):
                score += 10.0
                matched_factors.append("Matching Season")
                notes.append(f"Season '{season}' matches {crop.seasons}")

        if location and crop.locations:
            if CropInformation.matches(location, crop.locations):
                score += 5.0
                max_possible_score += 5.0
                matched_factors.append("Regional Suitability")
                notes.append(f"Region '{location}' is a proven cultivation zone for {crop.name}")

        # Baseline score if no criteria provided
        if max_possible_score == 0:
            max_possible_score = 10.0
            score = 5.0

        percentage = int(round((score / max_possible_score) * 100))
        explanation_text = " • ".join(notes) if notes else f"{crop.name} is generally suitable for current agricultural conditions."
        products = get_linked_marketplace_products(crop.name)

        scored_crops.append(
            RankedCropResult(
                crop=crop,
                score=score,
                suitability_percentage=percentage,
                matched_factors=matched_factors,
                explanation=explanation_text,
                marketplace_products=products,
            )
        )

    # Sort crops descending by suitability percentage
    scored_crops.sort(key=lambda item: (item.suitability_percentage, item.score, item.crop.name), reverse=True)

    top_crop = scored_crops[0].crop if scored_crops and scored_crops[0].suitability_percentage > 30 else (scored_crops[0].crop if scored_crops else None)
    top_explanation = (
        f"{top_crop.name} is your highest-scoring crop ({scored_crops[0].suitability_percentage}% compatibility). "
        f"{scored_crops[0].explanation}"
    ) if top_crop else "No suitable crop found matching the specified parameters."

    return CropRecommendationResult(
        primary_crop=top_crop,
        ranked_crops=scored_crops,
        explanation=top_explanation,
        recommendation_type="soil_parameters",
        input_summary={
            "n": n, "p": p, "k": k, "ph": ph, "rainfall": rainfall,
            "temperature": temperature, "soil_type": soil_type, "season": season, "location": location,
        },
        total_matches=len(scored_crops),
    )


def recommend_by_season(season: str, location: str = "") -> CropRecommendationResult:
    """Recommend crops suitable for a specific agricultural season (Kharif, Rabi, Zaid, Summer, Monsoon, Winter)."""
    crops = list(CropInformation.objects.all())
    matching_results: List[RankedCropResult] = []

    for crop in crops:
        is_season_match = CropInformation.matches(season, crop.seasons)
        is_loc_match = bool(location and crop.locations and CropInformation.matches(location, crop.locations))

        score = 0.0
        matched = []
        notes = []

        if is_season_match:
            score += 70.0
            matched.append(f"Season: {season}")
            notes.append(f"Optimal growth cycle during {season} season ({crop.seasons})")
        if is_loc_match:
            score += 30.0
            matched.append(f"Region: {location}")
            notes.append(f"Thrives in {location} regional climate")
        elif not location:
            score += 20.0

        if score > 0:
            percentage = min(100, int(score))
            products = get_linked_marketplace_products(crop.name)
            matching_results.append(
                RankedCropResult(
                    crop=crop,
                    score=score,
                    suitability_percentage=percentage,
                    matched_factors=matched,
                    explanation=" • ".join(notes),
                    marketplace_products=products,
                )
            )

    matching_results.sort(key=lambda r: (r.suitability_percentage, r.crop.name), reverse=True)
    top_crop = matching_results[0].crop if matching_results else None
    explanation = (
        f"Found {len(matching_results)} crop(s) recommended for the {season} season. "
        f"Top pick: {top_crop.name}."
    ) if top_crop else f"No crops currently listed for season '{season}'."

    return CropRecommendationResult(
        primary_crop=top_crop,
        ranked_crops=matching_results,
        explanation=explanation,
        recommendation_type="season",
        input_summary={"season": season, "location": location},
        total_matches=len(matching_results),
    )


def recommend_by_soil_type(soil_type: str, location: str = "") -> CropRecommendationResult:
    """Recommend crops based on soil physical structure (Clay, Loam, Sandy loam, Black soil, etc.)."""
    crops = list(CropInformation.objects.all())
    matching_results: List[RankedCropResult] = []

    for crop in crops:
        is_soil_match = CropInformation.matches(soil_type, crop.soil_types)
        is_loc_match = bool(location and crop.locations and CropInformation.matches(location, crop.locations))

        score = 0.0
        matched = []
        notes = []

        if is_soil_match:
            score += 70.0
            matched.append(f"Soil: {soil_type}")
            notes.append(f"Root architecture and aeration suited for {soil_type} soil ({crop.soil_types})")
        if is_loc_match:
            score += 30.0
            matched.append(f"Region: {location}")
            notes.append(f"Adapted to {location} conditions")
        elif not location:
            score += 20.0

        if score > 0:
            percentage = min(100, int(score))
            products = get_linked_marketplace_products(crop.name)
            matching_results.append(
                RankedCropResult(
                    crop=crop,
                    score=score,
                    suitability_percentage=percentage,
                    matched_factors=matched,
                    explanation=" • ".join(notes),
                    marketplace_products=products,
                )
            )

    matching_results.sort(key=lambda r: (r.suitability_percentage, r.crop.name), reverse=True)
    top_crop = matching_results[0].crop if matching_results else None
    explanation = (
        f"Found {len(matching_results)} crop(s) suitable for {soil_type} soil. "
        f"Top pick: {top_crop.name}."
    ) if top_crop else f"No crops currently listed for soil type '{soil_type}'."

    return CropRecommendationResult(
        primary_crop=top_crop,
        ranked_crops=matching_results,
        explanation=explanation,
        recommendation_type="soil_type",
        input_summary={"soil_type": soil_type, "location": location},
        total_matches=len(matching_results),
    )


def save_crop_recommendation_history(
    user,
    result: CropRecommendationResult,
    raw_params: Optional[Dict[str, Any]] = None,
) -> CropRecommendation:
    """Persist recommendation query and ranked outputs to user history."""
    params = raw_params or result.input_summary

    ranked_list = [
        {
            "crop_id": r.crop.id,
            "crop_name": r.crop.name,
            "score": r.score,
            "percentage": r.suitability_percentage,
            "explanation": r.explanation,
        }
        for r in result.ranked_crops[:5]
    ]

    def _clean_json_val(val):
        if isinstance(val, dict):
            return {k: _clean_json_val(v) for k, v in val.items()}
        if isinstance(val, list):
            return [_clean_json_val(v) for v in val]
        if isinstance(val, Decimal):
            return float(val)
        return val

    clean_input_params = _clean_json_val(params)

    rec = CropRecommendation.objects.create(
        user=user,
        soil_type=str(params.get("soil_type") or ""),
        season=str(params.get("season") or ""),
        location=str(params.get("location") or ""),
        temperature=Decimal(str(params["temperature"])) if params.get("temperature") is not None and params["temperature"] != "" else None,
        rainfall=Decimal(str(params["rainfall"])) if params.get("rainfall") is not None and params["rainfall"] != "" else None,
        ph=Decimal(str(params["ph"])) if params.get("ph") is not None and params["ph"] != "" else None,
        n=Decimal(str(params["n"])) if params.get("n") is not None and params["n"] != "" else None,
        p=Decimal(str(params["p"])) if params.get("p") is not None and params["p"] != "" else None,
        k=Decimal(str(params["k"])) if params.get("k") is not None and params["k"] != "" else None,
        input_params=clean_input_params,
        recommended_crop=result.primary_crop,
        recommended_crops_list=ranked_list,
        explanation=result.explanation,
    )
    return rec
