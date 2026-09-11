"""Web Views and Controllers for AI & Agriculture Module."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from agrivision.agriculture.forms import (
    AgricultureInfoSearchForm,
    CropRecommendationForm,
    DiseaseDetectionForm,
    MarketPriceFilterForm,
    SeasonRecommendationForm,
    SoilParamsRecommendationForm,
    SoilTypeRecommendationForm,
)
from agrivision.agriculture.models import (
    CropInformation,
    CropRecommendation,
    DiseaseDetection,
    DiseaseInformation,
    MarketPrice,
)
from agrivision.agriculture.services.agri_info import search_agricultural_info
from agrivision.agriculture.services.crop_recommendation import (
    get_linked_marketplace_products,
    recommend_by_season,
    recommend_by_soil_parameters,
    recommend_by_soil_type,
    save_crop_recommendation_history,
)
from agrivision.agriculture.services.disease_detection import DiseaseDetectionService
from agrivision.agriculture.services.market_price import get_market_prices


@login_required
def disease_detection(request):
    """Upload plant image for AI disease diagnosis."""
    if request.method == "POST":
        form = DiseaseDetectionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                service = DiseaseDetectionService()
                detection = service.process_and_record(request.user, form.cleaned_data["image"])
                messages.success(request, _("Image analyzed successfully!"))
                return redirect("agriculture:disease_result", pk=detection.pk)
            except Exception as exc:
                messages.error(request, _(f"Error processing image: {exc}"))
        else:
            messages.error(request, _("Please correct the errors in the upload form."))
    else:
        form = DiseaseDetectionForm()

    # Get user's recent detections for quick history preview
    recent_detections = DiseaseDetection.objects.filter(user=request.user)[:4]

    return render(
        request,
        "agriculture/disease_detection.html",
        {
            "form": form,
            "recent_detections": recent_detections,
        },
    )


@login_required
def disease_result(request, pk):
    """View detailed disease diagnosis and treatment guidance."""
    detection = get_object_or_404(DiseaseDetection, pk=pk, user=request.user)

    # Find matching marketplace products if a disease is associated with a crop
    suggested_products = []
    if detection.disease:
        # e.g., for "Tomato early blight", search marketplace for "Tomato" seeds/plants
        first_word = detection.disease.name.split()[0]
        suggested_products = get_linked_marketplace_products(first_word, limit=4)

    return render(
        request,
        "agriculture/disease_result.html",
        {
            "detection": detection,
            "suggested_products": suggested_products,
        },
    )


@login_required
def disease_history(request):
    """View complete history of user's disease diagnosis queries."""
    detections = DiseaseDetection.objects.filter(user=request.user).select_related("disease")
    paginator = Paginator(detections, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "agriculture/disease_history.html",
        {
            "page_obj": page_obj,
            "total_detections": detections.count(),
        },
    )


@login_required
def crop_recommendation(request):
    """Multi-criteria crop recommendation interface (Soil params, Season, Soil type)."""
    tab = request.GET.get("tab", "params")
    result = None

    soil_form = SoilParamsRecommendationForm(request.POST or None if request.POST.get("form_type") == "params" else None)
    season_form = SeasonRecommendationForm(request.POST or None if request.POST.get("form_type") == "season" else None)
    soil_type_form = SoilTypeRecommendationForm(request.POST or None if request.POST.get("form_type") == "soil_type" else None)

    if request.method == "POST":
        form_type = request.POST.get("form_type", "params")
        tab = form_type

        if form_type == "params" and soil_form.is_valid():
            data = soil_form.cleaned_data
            result = recommend_by_soil_parameters(
                n=float(data["n"]) if data.get("n") is not None else None,
                p=float(data["p"]) if data.get("p") is not None else None,
                k=float(data["k"]) if data.get("k") is not None else None,
                ph=float(data["ph"]) if data.get("ph") is not None else None,
                rainfall=float(data["rainfall"]) if data.get("rainfall") is not None else None,
                temperature=float(data["temperature"]) if data.get("temperature") is not None else None,
                soil_type=data.get("soil_type") or "",
                season=data.get("season") or "",
                location=data.get("location") or "",
            )
            save_crop_recommendation_history(request.user, result, raw_params=data)
            messages.success(request, _("Crop recommendations generated successfully!"))

        elif form_type == "season" and season_form.is_valid():
            data = season_form.cleaned_data
            result = recommend_by_season(season=data["season"], location=data.get("location") or "")
            save_crop_recommendation_history(request.user, result, raw_params=data)
            messages.success(request, _(f"Season recommendations for {data['season']} generated!"))

        elif form_type == "soil_type" and soil_type_form.is_valid():
            data = soil_type_form.cleaned_data
            result = recommend_by_soil_type(soil_type=data["soil_type"], location=data.get("location") or "")
            save_crop_recommendation_history(request.user, result, raw_params=data)
            messages.success(request, _(f"Soil recommendations for {data['soil_type']} generated!"))

    return render(
        request,
        "agriculture/crop_recommendation.html",
        {
            "active_tab": tab,
            "soil_form": soil_form,
            "season_form": season_form,
            "soil_type_form": soil_type_form,
            "result": result,
        },
    )


@login_required
def crop_history(request):
    """View past crop recommendations history for current user."""
    recommendations = CropRecommendation.objects.filter(user=request.user).select_related("recommended_crop")
    paginator = Paginator(recommendations, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "agriculture/crop_history.html",
        {
            "page_obj": page_obj,
            "total_count": recommendations.count(),
        },
    )


@login_required
def market_prices(request):
    """Agricultural commodity market price directory with search and filters."""
    crop_name = request.GET.get("crop", "").strip()
    market = request.GET.get("market", "").strip()
    region = request.GET.get("region", "").strip()

    prices = get_market_prices(crop_name=crop_name, market=market, region=region)
    paginator = Paginator(prices, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "agriculture/market_prices.html",
        {
            "page_obj": page_obj,
            "total_records": prices.count(),
            "query_crop": crop_name,
            "query_market": market,
            "query_region": region,
        },
    )


@login_required
def agriculture_info(request):
    """Searchable knowledge encyclopedia of crops and plant pathology."""
    query = request.GET.get("query", "").strip()
    info_type = request.GET.get("information_type", "").strip()

    crops, diseases = search_agricultural_info(query=query, information_type=info_type)

    return render(
        request,
        "agriculture/agriculture_info.html",
        {
            "crops": crops,
            "diseases": diseases,
            "query": query,
            "information_type": info_type,
            "total_crops": crops.count(),
            "total_diseases": diseases.count(),
        },
    )


@login_required
def agri_chatbot(request):
    """Interactive AI Agronomist Chatbot interface."""
    return render(request, "agriculture/chatbot.html")

