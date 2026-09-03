# Plant Disease ML Models Directory

This directory stores trained machine learning model files for the AgriVision Plant Disease Detection inference service.

## Supported Model Formats

You can drop any of the following trained models directly into this folder:

1. **TensorFlow / Keras HDF5 Model**:
   - File path: `ml-service/models/plant_disease_model.h5` or `ml-service/models/model.h5`
   - Framework: `tensorflow.keras.models.load_model(...)`

2. **PyTorch Model**:
   - File path: `ml-service/models/plant_disease_model.pt` or `ml-service/models/model.pt`
   - Framework: `torch.load(...)` or TorchScript `torch.jit.load(...)`

3. **ONNX Model**:
   - File path: `ml-service/models/plant_disease_model.onnx` or `ml-service/models/model.onnx`
   - Framework: `onnxruntime.InferenceSession(...)`

4. **Keras SavedModel Directory**:
   - Directory path: `ml-service/models/saved_model/`

---

## Expected Model Specifications

- **Input Dimension**: `(Batch, 224, 224, 3)` (RGB, scaled to `[0.0, 1.0]` or normalized with standard ImageNet mean/std `mean=[0.485, 0.456, 0.406]`, `std=[0.229, 0.224, 0.225]`).
- **Output**: Softmax probability distribution over the target plant disease classes.

### Default Target Classes

The microservice maps model output indices to the following standard agricultural disease classes:
0. `Tomato early blight`
1. `Tomato late blight`
2. `Rice blast`
3. `Rice brown spot`
4. `Wheat leaf rust`
5. `Potato late blight`
6. `Cotton leaf curl`
7. `Maize leaf spot`
8. `Healthy crop`

*Note: If no trained weight file is found in this directory, the microservice automatically runs in smart heuristic simulation mode so that development, testing, and UI integration work seamlessly without errors.*
