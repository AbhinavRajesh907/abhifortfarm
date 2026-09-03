import os

from .disease_model import DiseaseModel
from .disease_model import DiseaseModelUnavailable
from .preprocessing import prepare_image


def predict_disease(uploaded_image):
    """Predict disease data without inventing results when the model is absent."""
    model = DiseaseModel(os.environ.get("AGRICULTURE_DISEASE_MODEL_PATH"))
    try:
        if not model.available:
            raise DiseaseModelUnavailable(
                "No trained disease detection model is configured."
            )
        prepared_image = prepare_image(uploaded_image)
        prediction = model.predict(prepared_image)
    except DiseaseModelUnavailable as error:
        return {
            "disease": None,
            "confidence": None,
            "treatment": "A trained disease model must be configured before treatment can be suggested.",
            "prevention": "Use the agricultural information pages or consult an agronomist until a model is configured.",
            "available": False,
            "error": str(error),
        }
    return {**prediction, "available": True, "error": None}
