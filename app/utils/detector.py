import os
import cv2
from huggingface_hub import hf_hub_download
from ultralytics import YOLO

class PotholeDetector:
    def __init__(self, model_path=None):
        if model_path is None:
            # Download the model from HF Hub
            try:
                print("Downloading model from Hugging Face Hub...")
                model_path = hf_hub_download(
                    repo_id="RohithGangarapu/PotholeYolov8",
                    filename="best.pt"
                )
                print(f"Model downloaded to {model_path}")
            except Exception as e:
                print(f"Error downloading model from HF Hub: {str(e)}")
                # Fallback to local if download fails
                model_path = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'best.pt')
        
        self.model_path = model_path
        self.model = None
        
        if model_path and os.path.exists(model_path):
            self.model = YOLO(model_path)
            print(f"Pothole model loaded from {model_path}")
        else:
            print(f"Warning: Pothole model not found or failed to load.")

    def detect(self, image_path):
        """
        Runs detection, draws annotations on the image, and returns 
        (list of detections, annotated_image_bytes).
        """
        if self.model is None:
            print("Model not loaded, skipping detection.")
            return [], None

        # Run inference
        results = self.model.predict(source=image_path, conf=0.25, save=False, verbose=False)
        detections = []
        
        # Load image for annotation
        img = cv2.imread(image_path)
        img_h, img_w, _ = img.shape

        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                
                # Heuristics for depth
                width = x2 - x1
                height = y2 - y1
                area = width * height
                rel_area = area / (img_h * img_w)
                
                # Depth Heuristic: rel_area * coefficient
                depth = round(rel_area * 50, 2)
                
                # Severity mapping based on depth
                if depth > 15:
                    severity = 'high'
                    color = (0, 0, 255) # Red
                elif depth > 5:
                    severity = 'medium'
                    color = (0, 165, 255) # Orange
                else:
                    severity = 'low'
                    color = (0, 255, 0) # Green
                
                # Annotation: Draw Bounding Box
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)
                
                # Annotation: Draw Label (Pothole + Depth)
                label = f"Pothole: {depth}cm"
                cv2.putText(img, label, (int(x1), int(y1) - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                detections.append({
                    'bbox': [x1, y1, x2, y2],
                    'confidence': conf,
                    'severity': severity,
                    'depth': depth,
                })
        
        # Convert annotated image back to bytes for Django
        success, buffer = cv2.imencode('.jpg', img)
        annotated_image_bytes = buffer.tobytes() if success else None
        
        return detections, annotated_image_bytes
