"""AI Agronomist Chatbot Engine for Agriculture Module.

Processes natural language queries and plant leaf uploads, orchestrating AI disease detection,
crop recommendations, market price queries, and agronomic knowledge retrieval.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

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

logger = logging.getLogger(__name__)


@dataclass
class ChatbotResponse:
    reply_text: str
    intent: str
    data: Dict[str, Any] = field(default_factory=dict)
    quick_replies: List[str] = field(default_factory=list)
    created_record_id: Optional[int] = None
    record_type: Optional[str] = None


def validate_plant_or_seed_image(pil_image: Any) -> Tuple[bool, str]:
    """Validate if the uploaded image is a plant leaf, crop, or seed photo."""
    try:
        import numpy as np
        rgb_img = pil_image.convert("RGB").resize((120, 120))
        arr = np.array(rgb_img, dtype=np.float32) / 255.0

        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        total_pixels = float(r.size)

        max_c = np.maximum(r, np.maximum(g, b))
        min_c = np.minimum(r, np.minimum(g, b))
        delta = max_c - min_c

        s = np.zeros_like(max_c)
        mask_max_non_zero = max_c > 0
        s[mask_max_non_zero] = delta[mask_max_non_zero] / max_c[mask_max_non_zero]
        v = max_c

        h = np.zeros_like(max_c)
        mask_r = (max_c == r) & (delta > 0)
        h[mask_r] = (60.0 * ((g[mask_r] - b[mask_r]) / delta[mask_r]) + 360.0) % 360.0

        mask_g = (max_c == g) & (delta > 0)
        h[mask_g] = (60.0 * ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 120.0) % 360.0

        mask_b = (max_c == b) & (delta > 0)
        h[mask_b] = (60.0 * ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 240.0) % 360.0

        # Plant & Seed Pixel Masks
        green_mask = (h >= 35) & (h <= 165) & (s >= 0.15) & (v >= 0.15) & (g > b)
        yellow_leaf_mask = (h >= 20) & (h < 35) & (s >= 0.20) & (v >= 0.20) & (g >= b - 0.05) & (r > b)
        brown_leaf_mask = (h >= 10) & (h < 25) & (s >= 0.15) & (s <= 0.85) & (v >= 0.12) & (v <= 0.80) & (r > b)
        seed_mask = (h >= 12) & (h <= 55) & (s >= 0.15) & (v >= 0.20) & (r >= b + 0.05)

        plant_seed_mask = green_mask | yellow_leaf_mask | brown_leaf_mask | seed_mask
        plant_seed_pixel_count = int(np.sum(plant_seed_mask))
        plant_seed_ratio = plant_seed_pixel_count / total_pixels

        low_sat_pixels = int(np.sum(s < 0.18))
        low_sat_ratio = low_sat_pixels / total_pixels

        blue_pixels = int(np.sum((b > g + 0.10) & (b > r + 0.10)))
        blue_ratio = blue_pixels / total_pixels

        green_ratio = int(np.sum(green_mask)) / total_pixels

        if plant_seed_ratio < 0.32:
            return False, "⚠️ **Non-Plant / Seed Image Detected**\n\nPlease upload a clear close-up photo of a plant leaf, crop, or seeds. Non-agricultural photos (such as room interiors, furniture, or generic objects) cannot be processed."

        if low_sat_ratio > 0.65 and green_ratio < 0.20:
            return False, "⚠️ **Indoor Room / Furniture Image Detected**\n\nPlease upload a clear photo focusing on a plant leaf, crop, or seed rather than room background or furniture."

        if blue_ratio > 0.45:
            return False, "⚠️ **Non-Agricultural Image Detected**\n\nPlease upload a clear photo of a plant leaf, crop, or seeds for disease diagnosis."

        return True, ""
    except Exception as exc:
        return True, ""


class AgriChatbotService:
    """Intelligent Agrononomist Assistant for AgriVision."""

    def __init__(self, disease_service: Optional[DiseaseDetectionService] = None):
        self.disease_service = disease_service or DiseaseDetectionService()

    def process_message(
        self,
        user,
        message: str = "",
        image_file: Any = None,
    ) -> ChatbotResponse:
        """Main entrypoint to process user message text and/or image upload."""
        clean_text = (message or "").strip()

        # 1. Direct Leaf Photo Upload Intent
        if image_file:
            return self._handle_image_upload(user, image_file, clean_text)

        if not clean_text:
            return ChatbotResponse(
                reply_text="Hello! I am your AI Agronomist Assistant. 🌾\n\nYou can upload a plant leaf photo for disease diagnosis, ask for crop recommendations, check market prices, or inquire about plant health advice.",
                intent="greeting",
                quick_replies=[
                    "📸 Diagnose Plant Leaf Photo",
                    "🌱 Recommend Best Crops",
                    "📈 Check Market Prices",
                    "🍂 Kharif Season Advisory",
                ],
            )

        lower_text = clean_text.lower()

        # 2. Intent Classification
        if any(w in lower_text for w in ["price", "cost", "rate", "market", "quintal", "mandi"]):
            return self._handle_market_price_query(clean_text)

        if any(w in lower_text for w in ["recommend", "soil", "season", "grow", "suitable", "crop for", "plant for", "npk"]):
            return self._handle_crop_recommendation_query(user, clean_text)

        if any(w in lower_text for w in ["disease", "blight", "rust", "spot", "symptom", "rot", "wilt", "treat", "cure"]):
            return self._handle_disease_info_query(clean_text)

        if any(w in lower_text for w in ["hello", "hi", "hey", "help", "who are you", "what can you do"]):
            return ChatbotResponse(
                reply_text=(
                    "Greetings, Farmer! 🌱 I am **AgriBot**, your AI-powered agricultural advisor.\n\n"
                    "**Here is how I can assist you:**\n"
                    "1. 📸 **Disease Detection**: Upload a leaf image to diagnose diseases and get treatment steps.\n"
                    "2. 🌱 **Crop Advisory**: Tell me your soil parameters, season, or soil type for optimal crop matching.\n"
                    "3. 📈 **Market Prices**: Ask for prices of crops like Rice, Wheat, Cotton, or Tomato.\n"
                    "4. 📖 **Agronomic Library**: Ask questions about cultivation, soil pH, fertilizers, or prevention methods."
                ),
                intent="greeting",
                quick_replies=[
                    "📸 Diagnose Plant Leaf Photo",
                    "🌱 Recommended crops for Loam soil",
                    "🍂 Best crops for Kharif season",
                    "📈 Market prices for Rice",
                ],
            )

        # 3. Fallback / Search Encyclopedia
        return self._handle_general_query(clean_text)

    def _handle_image_upload(self, user, image_file, caption: str) -> ChatbotResponse:
        """Process image upload via DiseaseDetectionService and persist DB record."""
        # Non-plant image color & spectrum validation
        try:
            import io
            from PIL import Image

            if hasattr(image_file, "read"):
                bdata = image_file.read()
                if hasattr(image_file, "seek"):
                    image_file.seek(0)
            elif isinstance(image_file, bytes):
                bdata = image_file
            else:
                bdata = None

            if bdata:
                p_img = Image.open(io.BytesIO(bdata))
                is_valid_plant, err_msg = validate_plant_or_seed_image(p_img)
                if not is_valid_plant:
                    return ChatbotResponse(
                        reply_text=err_msg,
                        intent="disease_detection_error",
                        quick_replies=["📸 Upload Plant or Seed Photo", "🌱 Recommend best crops"],
                    )
        except Exception as exc:
            logger.debug("Non-plant PIL check skipped: %s", exc)

        try:
            detection = self.disease_service.process_and_record(user, image_file)

            disease_name = detection.disease.name if detection.disease else "Unclassified / General Plant Issue"
            conf_str = f"{detection.confidence_percentage}%" if detection.confidence is not None else "N/A"
            severity = detection.disease.severity.capitalize() if detection.disease else "Medium"

            reply_lines = [
                f"### 🔬 AI Disease Diagnosis Completed",
                f"**Diagnosis**: {disease_name}",
                f"**AI Confidence**: `{conf_str}`",
                f"**Severity**: `{severity}`",
                "",
                f"**💊 Treatment Guidance:**\n{detection.treatment}",
                "",
                f"**🛡️ Preventive Measures:**\n{detection.prevention}",
            ]

            # Link marketplace products
            products_data = []
            if detection.disease:
                first_word = detection.disease.name.split()[0]
                prods = get_linked_marketplace_products(first_word, limit=3)
                products_data = [
                    {"id": p.id, "name": p.name, "price": float(p.price), "category": p.category.name}
                    for p in prods
                ]
                if products_data:
                    reply_lines.append("\n**🛒 Recommended Marketplace Seeds & Supplies:**")
                    for p in products_data:
                        reply_lines.append(f"- **{p['name']}** — ₹{p['price']} ({p['category']})")

            return ChatbotResponse(
                reply_text="\n".join(reply_lines),
                intent="disease_detection",
                data={
                    "detection_id": detection.id,
                    "disease": disease_name,
                    "confidence": conf_str,
                    "treatment": detection.treatment,
                    "prevention": detection.prevention,
                    "status": detection.status,
                    "image_url": detection.image.url if detection.image else None,
                    "products": products_data,
                },
                quick_replies=[
                    "📖 Tell me more about this disease",
                    "🌱 Recommend alternative crops",
                    "📈 Check market price for this crop",
                ],
                created_record_id=detection.id,
                record_type="DiseaseDetection",
            )
        except Exception as exc:
            logger.exception("Chatbot image diagnosis failed: %s", exc)
            return ChatbotResponse(
                reply_text=f"⚠️ Sorry, an error occurred while processing your plant leaf image: {str(exc)}",
                intent="disease_detection_error",
                quick_replies=["Try uploading photo again", "Ask standard agronomy question"],
            )

    def _handle_crop_recommendation_query(self, user, query: str) -> ChatbotResponse:
        """Parse soil/season parameters from text query and generate crop recommendations."""
        lower_q = query.lower()

        # Season check
        matched_season = None
        for s in ["kharif", "rabi", "summer", "monsoon", "winter", "autumn"]:
            if s in lower_q:
                matched_season = s.capitalize()
                break

        # Soil type check
        matched_soil = None
        for st in ["clay loam", "sandy loam", "sandy", "clay", "loam", "black", "red", "alluvial", "silt"]:
            if st in lower_q:
                matched_soil = st.title()
                break

        # Parse numeric parameters if available (e.g. "pH 6.5", "temp 28", "npk 80 40 40")
        ph_match = re.search(r"ph\s*[:=]?\s*(\d+(?:\.\d+)?)", lower_q)
        ph = float(ph_match.group(1)) if ph_match else None

        temp_match = re.search(r"(?:temp|temperature)\s*[:=]?\s*(\d+(?:\.\d+)?)", lower_q)
        temp = float(temp_match.group(1)) if temp_match else None

        npk_match = re.search(r"npk\s*[:=]?\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)", lower_q)
        n, p, k = (float(npk_match.group(1)), float(npk_match.group(2)), float(npk_match.group(3))) if npk_match else (None, None, None)

        if matched_season and not matched_soil and not ph:
            rec_result = recommend_by_season(season=matched_season)
            rec_type = f"Season-Based ({matched_season})"
        elif matched_soil and not ph and not npk_match:
            rec_result = recommend_by_soil_type(soil_type=matched_soil)
            rec_type = f"Soil Type-Based ({matched_soil})"
        else:
            rec_result = recommend_by_soil_parameters(
                n=n, p=p, k=k, ph=ph, temperature=temp, soil_type=matched_soil or "", season=matched_season or ""
            )
            rec_type = "Multi-Parameter Soil Advisory"

        # Save to DB if authenticated
        history_id = None
        if user and user.is_authenticated:
            history_obj = save_crop_recommendation_history(user, rec_result, raw_params={"query": query})
            history_id = history_obj.id

        reply_lines = [
            f"### 🌱 Crop Recommendation Results ({rec_type})",
            f"{rec_result.explanation}",
            "",
            "**Ranked Recommendations:**",
        ]

        crops_payload = []
        for idx, item in enumerate(rec_result.ranked_crops[:4], 1):
            crop_name = item.crop.name
            score = item.suitability_percentage
            reply_lines.append(f"{idx}. **{crop_name}** — Match Score: `{score:.1f}%`")
            reply_lines.append(f"   _{item.explanation}_")
            crops_payload.append({
                "crop_name": crop_name,
                "score": score,
                "explanation": item.explanation,
            })

        reply_lines.append("\n💡 *Tip: For precise AI recommendations, try specifying Nitrogen, Phosphorus, Potassium (N-P-K) or soil pH.*")

        return ChatbotResponse(
            reply_text="\n".join(reply_lines),
            intent="crop_recommendation",
            data={"recommendations": crops_payload, "rec_type": rec_type},
            quick_replies=[
                "🍂 Recommend crops for Rabi season",
                "🪴 Recommend crops for Clay soil",
                "📈 Check market prices for recommended crops",
            ],
            created_record_id=history_id,
            record_type="CropRecommendation",
        )

    def _handle_market_price_query(self, query: str) -> ChatbotResponse:
        """Extract crop names from query and return live market price records."""
        all_crops = CropInformation.objects.values_list("name", flat=True)
        matched_crops = [cname for cname in all_crops if cname.lower() in query.lower()]

        if matched_crops:
            prices = MarketPrice.objects.filter(crop__name__in=matched_crops).select_related("crop")
        else:
            prices = get_market_prices(crop_name="")

        if not prices.exists():
            return ChatbotResponse(
                reply_text=f"📈 No current market prices recorded matching '{query}'. Try asking for specific crops like Rice, Wheat, Tomato, or Cotton.",
                intent="market_price",
                quick_replies=["Wheat market price", "Rice market price", "Tomato market price"],
            )

        reply_lines = [
            f"### 📈 Commodity Market Prices",
            f"Found **{prices.count()}** active price records:",
            "",
        ]

        prices_payload = []
        for p in prices[:6]:
            reply_lines.append(f"- **{p.crop.name}**: ₹{p.price:.2f} / {p.unit} at *{p.market}* ({p.region or 'National'})")
            prices_payload.append({
                "crop": p.crop.name,
                "price": float(p.price),
                "unit": p.unit,
                "market": p.market,
                "region": p.region,
            })

        return ChatbotResponse(
            reply_text="\n".join(reply_lines),
            intent="market_price",
            data={"prices": prices_payload},
            quick_replies=["🌱 Recommend crops for high market price", "📸 Check leaf disease"],
        )

    def _handle_disease_info_query(self, query: str) -> ChatbotResponse:
        """Search plant pathology encyclopedia for disease information."""
        crops, diseases = search_agricultural_info(query=query, information_type="disease")
        if not diseases.exists():
            return ChatbotResponse(
                reply_text=f"🦠 No specific disease entry found for '{query}'.\n\n💡 *Tip: Upload a leaf photo using the photo button below for instant AI diagnosis!*",
                intent="agri_info",
                quick_replies=["📸 Upload Plant Leaf Photo", "🌾 Show common crop diseases"],
            )

        disease = diseases.first()
        reply_lines = [
            f"### 🦠 Disease Spotlight: {disease.name}",
            f"**Description**: {disease.description}",
            f"**Severity**: `{disease.severity.capitalize()}`",
            "",
            f"**Symptoms:**\n{disease.symptoms or 'Discolored spots, wilting, or yellowing leaves.'}",
            "",
            f"**💊 Treatment:**\n{disease.treatment}",
            "",
            f"**🛡️ Prevention:**\n{disease.prevention}",
        ]

        return ChatbotResponse(
            reply_text="\n".join(reply_lines),
            intent="agri_info",
            data={
                "disease_id": disease.id,
                "name": disease.name,
                "severity": disease.severity,
            },
            quick_replies=["📸 Diagnose Plant Leaf Photo", "🌱 Recommend healthy crops"],
        )

    def _handle_general_query(self, query: str) -> ChatbotResponse:
        """Fallback agronomic search across crops and diseases."""
        crops, diseases = search_agricultural_info(query=query)

        if crops.exists() or diseases.exists():
            reply_lines = ["### 🌾 Agricultural Knowledge Search Results\n"]

            if crops.exists():
                c = crops.first()
                reply_lines.append(f"**Crop Info: {c.name}**")
                reply_lines.append(f"- *Overview*: {c.description[:180]}...")
                reply_lines.append(f"- *Seasons*: {c.seasons}")
                reply_lines.append(f"- *Soil Types*: {c.soil_types}\n")

            if diseases.exists():
                d = diseases.first()
                reply_lines.append(f"**Disease Info: {d.name}**")
                reply_lines.append(f"- *Treatment*: {d.treatment[:180]}...\n")

            return ChatbotResponse(
                reply_text="\n".join(reply_lines),
                intent="agri_info",
                quick_replies=["📸 Diagnose leaf photo", "🌱 Recommended crops", "📈 Market prices"],
            )

        return ChatbotResponse(
            reply_text=(
                f"I processed your query: *\"{query}\"*.\n\n"
                "I am specialized in:\n"
                "- 📸 **Diagnosing plant diseases** from uploaded leaf photos\n"
                "- 🌱 **Recommending optimal crops** based on soil pH, NPK, and season\n"
                "- 📈 **Retrieving commodity market prices**\n"
                "- 📖 **Answering agronomic & disease questions**\n\n"
                "Please try uploading a leaf photo or selecting one of the quick options below!"
            ),
            intent="general_fallback",
            quick_replies=[
                "📸 Upload Leaf Photo",
                "🌱 Recommend crops for Loam soil",
                "📈 Wheat market price",
            ],
        )
