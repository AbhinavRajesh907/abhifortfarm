"""AI Plant Disease Detection Service and ML Microservice Client.

Integrates the backend with the FastAPI ML inference microservice via REST / HTTP,
enriches raw predictions with treatments & preventive measures from the database,
and saves the detection history for the user.
"""

from dataclasses import dataclass
import io
import logging
from typing import Any, Dict, Optional

from django.conf import settings
import requests

from agrivision.agriculture.models import DiseaseDetection
from agrivision.agriculture.models import DiseaseInformation

logger = logging.getLogger(__name__)


@dataclass
class DiseasePredictionResult:
    disease_name: Optional[str]
    confidence: Optional[float]
    status: str
    treatment: str
    prevention: str
    disease_obj: Optional[DiseaseInformation]
    raw_response: Dict[str, Any]
    error: Optional[str] = None


class MLServiceClient:
    """Client for the standalone FastAPI ML Inference Microservice."""

    def __init__(self, base_url: Optional[str] = None, timeout: int = 10):
        self.base_url = (base_url or getattr(settings, "ML_SERVICE_URL", "http://localhost:8001")).rstrip("/")
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        """Query ML microservice health endpoint."""
        url = f"{self.base_url}/health"
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            return {"status": "unhealthy", "code": response.status_code}
        except Exception as exc:
            logger.warning(f"ML microservice health check failed: {exc}")
            return {"status": "unreachable", "error": str(exc)}

    def predict(self, image_file, filename: str = "leaf.jpg") -> Dict[str, Any]:
        """Send image to ML microservice POST /predict endpoint."""
        url = f"{self.base_url}/predict"
        try:
            # Read file bytes
            if hasattr(image_file, "read"):
                image_bytes = image_file.read()
                if hasattr(image_file, "seek"):
                    image_file.seek(0)
            elif isinstance(image_file, bytes):
                image_bytes = image_file
            else:
                raise ValueError("Unsupported image file object")

            files = {"image": (filename, io.BytesIO(image_bytes), "image/jpeg")}
            response = requests.post(url, files=files, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"ML Service returned HTTP {response.status_code}: {response.text}")
                return {
                    "status": "error",
                    "error": f"ML microservice error (HTTP {response.status_code})",
                    "disease": None,
                    "confidence": None,
                }
        except requests.exceptions.RequestException as exc:
            logger.warning(f"Failed to communicate with ML microservice at {url}: {exc}")
            return {
                "status": "unreachable",
                "error": f"ML microservice unavailable: {str(exc)}",
                "disease": None,
                "confidence": None,
            }


class DiseaseDetectionService:
    """High-level disease detection coordinator."""

    def __init__(self, client: Optional[MLServiceClient] = None):
        self.client = client or MLServiceClient()

    def process_and_record(self, user, uploaded_image) -> DiseaseDetection:
        """Uploads image to ML service, maps to database knowledge, and persists record."""
        # 1. Reset file pointer before sending to ML service
        if hasattr(uploaded_image, "seek"):
            uploaded_image.seek(0)

        filename = getattr(uploaded_image, "name", "leaf.jpg")
        prediction_data = self.client.predict(uploaded_image, filename=filename)

        # 2. Extract prediction details
        disease_name = prediction_data.get("disease")
        confidence = prediction_data.get("confidence")
        status_raw = prediction_data.get("status", "error")

        disease_obj = None
        treatment = ""
        prevention = ""
        detection_status = DiseaseDetection.COMPLETE

        if status_raw == "success" and disease_name:
            # Search database for matching disease treatment & prevention info
            disease_obj = DiseaseInformation.objects.filter(name__iexact=disease_name).first()
            if not disease_obj:
                # Partial / fallback matching
                disease_obj = DiseaseInformation.objects.filter(name__icontains=disease_name.split()[0]).first()

            if disease_obj:
                treatment = disease_obj.treatment
                prevention = disease_obj.prevention
            else:
                treatment = f"Standard agricultural disease management protocol for {disease_name}. Consult local agronomist."
                prevention = "Maintain adequate crop spacing, clean equipment, and practice crop rotation."
        elif status_raw == "unreachable":
            # Microservice is offline -> Provide graceful guidance and mark unavailable
            detection_status = DiseaseDetection.UNAVAILABLE
            treatment = (
                "The AI disease inference microservice is currently offline. "
                "Ensure 'ml-service' is running on port 8001 or consult an agricultural specialist."
            )
            prevention = "Refer to the Agricultural Information library for common crop disease symptoms and management."
        else:
            detection_status = DiseaseDetection.PENDING
            treatment = "Diagnosis pending or could not be determined from the provided image."
            prevention = "Please ensure the leaf photo is clear, well-lit, and in focus."

        # 3. Create DiseaseDetection entity
        if hasattr(uploaded_image, "seek"):
            uploaded_image.seek(0)

        detection = DiseaseDetection.objects.create(
            user=user,
            image=uploaded_image,
            disease=disease_obj,
            confidence=confidence,
            treatment=treatment,
            prevention=prevention,
            status=detection_status,
        )
        return detection
