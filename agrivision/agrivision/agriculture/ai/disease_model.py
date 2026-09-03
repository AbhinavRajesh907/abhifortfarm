from pathlib import Path


class DiseaseModelUnavailable(RuntimeError):
    """Raised when no trained disease model has been configured."""


class DiseaseModel:
    """Adapter for a future trained model; it never fabricates predictions."""

    def __init__(self, model_path=None):
        self.model_path = Path(model_path) if model_path else None
        self._model = None

    @property
    def available(self):
        return bool(self.model_path and self.model_path.is_file())

    def predict(self, image):
        if not self.available:
            raise DiseaseModelUnavailable(
                "No trained disease detection model is configured."
            )
        raise NotImplementedError(
            "Implement prediction for the configured model format before enabling it."
        )
