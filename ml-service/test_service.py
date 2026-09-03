"""Unit and integration tests for FastAPI ML Inference Service."""

import io
import sys
import unittest

from fastapi.testclient import TestClient
from PIL import Image

try:
    from app import app
except ImportError:
    from ml_service.app import app


class TestMLService(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertIn("service", data)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_loaded"])
        self.assertGreater(data["supported_classes_count"], 0)

    def test_predict_valid_image(self):
        # Create a synthetic 100x100 RGB image in memory
        img = Image.new("RGB", (100, 100), color=(73, 109, 137))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        response = self.client.post(
            "/predict",
            files={"image": ("test_leaf.jpg", buf, "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("disease", data)
        self.assertIn("confidence", data)
        self.assertIsInstance(data["confidence"], (float, int))
        self.assertGreaterEqual(data["confidence"], 0.0)
        self.assertLessEqual(data["confidence"], 1.0)

    def test_predict_missing_file(self):
        response = self.client.post("/predict")
        self.assertEqual(response.status_code, 400)

    def test_predict_invalid_mime(self):
        buf = io.BytesIO(b"dummy text file content")
        response = self.client.post(
            "/predict",
            files={"image": ("test.txt", buf, "text/plain")},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
