# AgriVision - ML Inference Microservice (Plant Disease Detection)

This directory contains the standalone **AI Plant Disease Detection Microservice** for the AgriVision agriculture platform. Built with **FastAPI**, it provides high-throughput image classification inference for plant leaf images.

---

## Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Frontend (Web / App)    │
                          └─────────────┬─────────────┘
                                        │ Upload Image
                                        ▼
                          ┌───────────────────────────┐
                          │  Spring Boot / Django API │
                          └─────────────┬─────────────┘
                                        │ HTTP POST /predict
                                        ▼
               ┌─────────────────────────────────────────────────┐
               │    FastAPI ML Inference Service (:8001)         │
               │                                                 │
               │  1. Preprocessing (Resize, RGB, Normalize)     │
               │  2. Model Adapter:                              │
               │     ├── Custom Weights (model.h5 / model.pt)    │
               │     └── Smart Heuristic Classifier (Fallback)   │
               │  3. Return: {"disease": "...", "confidence": 0.94}│
               └─────────────────────────────────────────────────┘
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (Python 3.11 / 3.12 / 3.13 supported)

### 2. Install Dependencies
```bash
cd ml-service
pip install -r requirements.txt
```

### 3. Run the Service
```bash
# Start with Uvicorn on port 8001
uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# Or directly with Python
python app.py
```

The service will be available at:
- **Root**: `http://localhost:8001/`
- **Health check**: `http://localhost:8001/health`
- **Interactive Swagger Docs**: `http://localhost:8001/docs`

---

## API Endpoints

### 1. `GET /health`
Returns service and model loading status.
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_type": "Built-in Agronomic Heuristic Classifier (Demo Mode)",
  "supported_classes_count": 9,
  "supported_classes": [
    "Tomato early blight",
    "Tomato late blight",
    "Rice blast",
    "Rice brown spot",
    "Wheat leaf rust",
    "Potato late blight",
    "Cotton leaf curl",
    "Maize leaf spot",
    "Healthy crop"
  ]
}
```

### 2. `POST /predict`
Accepts multipart image upload (`multipart/form-data` with field `image`).

**Example cURL Request**:
```bash
curl -X POST "http://localhost:8001/predict" \
  -F "image=@/path/to/leaf_sample.jpg"
```

**Example JSON Response**:
```json
{
  "disease": "Tomato early blight",
  "confidence": 0.925,
  "status": "success",
  "model_type": "Agronomic Heuristic Engine",
  "metadata": {
    "greenness_ratio": 0.612,
    "spot_variance": 0.204
  }
}
```

---

## How to Plug In a Real Trained ML Model

1. **Train your model** (e.g., using ResNet, MobileNetV3, EfficientNet, or CNN on the PlantVillage dataset).
2. **Export your model weights**:
   - **Keras / TensorFlow**: Save as `plant_disease_model.h5` or `model.h5`
   - **PyTorch**: Save as TorchScript `plant_disease_model.pt` (`torch.jit.save(...)`)
   - **ONNX**: Save as `plant_disease_model.onnx`
3. **Drop the weights file** into the `ml-service/models/` folder:
   ```
   ml-service/
   ├── app.py
   ├── requirements.txt
   └── models/
       ├── plant_disease_model.h5   <-- Drop file here!
       └── README.md
   ```
4. **Restart the microservice**:
   The service automatically detects the weights file, switches to the deep learning framework, and logs:
   `Successfully loaded Keras model from: .../models/plant_disease_model.h5`

---

## Running Automated Tests

Run the test script to verify both the health and prediction endpoints:
```bash
python test_service.py
```
