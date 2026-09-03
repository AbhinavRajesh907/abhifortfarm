from PIL import Image


class ImagePreprocessingError(ValueError):
    """Raised when a validated image cannot be prepared for prediction."""


def prepare_image(uploaded_image, size=(224, 224)):
    """Return a normalized RGB image ready for a model adapter."""
    try:
        with Image.open(uploaded_image) as image:
            return image.convert("RGB").resize(size)
    except (OSError, ValueError) as error:
        raise ImagePreprocessingError("Unable to preprocess the uploaded image.") from error
