import anvil.server
from anvil.files import data_files
import onnxruntime as ort
import numpy as np
from PIL import Image
import io

# --- INITIALIZATION ---

# 1. Load Model (ensure file name matches exactly in Data Files)
model_path = data_files['squeezenet1.1-7.onnx']
session = ort.InferenceSession(model_path)
input_name = session.get_inputs()[0].name

# 2. Load Labels
# Ensure 'imagenet_classes.txt' has 1,000 lines starting with 'tench'
labels_path = data_files['imagenet-simple-labels.json.txt']
with open(labels_path, 'r') as f:
  CATEGORY_NAMES = [line.strip() for line in f.readlines()]

@anvil.server.callable
def get_category_name(category_id):
  """Maps the numeric ID from the model to the text label."""
  try:
    idx = int(category_id)
    if 0 <= idx < len(CATEGORY_NAMES):
      return CATEGORY_NAMES[idx]
    return f"Unknown ID: {idx}"
  except:
    return "Mapping Error"

@anvil.server.callable
def detect_with_onnx(file):
  # 1. Open and Resize
  img = Image.open(io.BytesIO(file.get_bytes())).convert('RGB')
  img = img.resize((224, 224), Image.Resampling.BILINEAR)

  # 2. Convert to NumPy and Normalize (float32)
  # Division by 255.0 converts 0-255 to 0.0-1.0
  img_data = np.array(img).astype(np.float32) / 255.0

  # 3. Apply ImageNet Mean and StdDev
  mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
  std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
  img_data = (img_data - mean) / std

  # 4. Transpose from (H, W, C) to (C, H, W)
  img_data = img_data.transpose(2, 0, 1)

  # 5. Add Batch Dimension: (1, 3, 224, 224)
  img_data = np.expand_dims(img_data, axis=0)

  # 6. Run Inference
  # session.run returns a list of results; we take the first one [0]
  raw_outputs = session.run(None, {input_name: img_data})
  predictions = raw_outputs[0].flatten()

  # 7. Get highest probability index
  result_index = np.argmax(predictions)

  # 8. Return the human-readable name
  return get_category_name(result_index)
