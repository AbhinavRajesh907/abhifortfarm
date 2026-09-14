"""URL routing for AI & Agriculture Module (Web Views & REST API Endpoints)."""

from django.urls import path

from . import api_views
from . import views

app_name = "agriculture"

urlpatterns = [
    # --------------------------------------------------------------------------
    # Web UI Views
    # --------------------------------------------------------------------------
    path("", views.smart_assistant, name="index"),
    path("smart-assistant/", views.smart_assistant, name="smart_assistant"),
    # AI Agronomist Chatbot
    path("chatbot/", views.agri_chatbot, name="chatbot"),
    path("disease-detection/", views.disease_detection, name="disease_detection"),
    path("disease-detection/<int:pk>/", views.disease_result, name="disease_result"),
    path("disease-detection/history/", views.disease_history, name="disease_history"),
    # Crop & Farming Recommendations
    path("crop-recommendation/", views.crop_recommendation, name="crop_recommendation"),
    path("crop-recommendation/history/", views.crop_history, name="crop_history"),
    # Market Prices & Agricultural Library
    path("market-prices/", views.market_prices, name="market_prices"),
    path("agriculture-info/", views.agriculture_info, name="agriculture_info"),
    # --------------------------------------------------------------------------
    # REST API Endpoints (JSON)
    # --------------------------------------------------------------------------
    # AI Chatbot API
    path("api/chatbot/", api_views.api_agri_chatbot, name="api_agri_chatbot"),
    # AI Disease Detection API
    path("api/disease-detection/upload/", api_views.api_disease_detection_upload, name="api_disease_detection_upload"),
    path("api/disease-detection/history/", api_views.api_disease_detection_history, name="api_disease_detection_history"),
    # Crop Recommendations API
    path("api/recommendations/crop/", api_views.api_recommend_crop, name="api_recommend_crop"),
    path("api/recommendations/season/", api_views.api_recommend_season, name="api_recommend_season"),
    path("api/recommendations/soil/", api_views.api_recommend_soil, name="api_recommend_soil"),
    path("api/crop-recommendations/history/", api_views.api_crop_recommendations_history, name="api_crop_recommendations_history"),
    # Market Price & Agri Info API
    path("api/market-prices/", api_views.api_market_prices, name="api_market_prices"),
    path("api/agri-info/", api_views.api_agri_info, name="api_agri_info"),
]

