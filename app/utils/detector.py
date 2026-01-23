import cv2
import numpy as np
from gradio_client import Client, handle_file
import os

class PotholeDetector:
    def __init__(self):
        # Initialize Gradio Client pointing to your Space
        self.space_id = "RohithGangarapu/PotholeYolov8"
        try:
            self.client = Client(self.space_id)
            print(f"Connected to Hugging Face Space: {self.space_id}")
        except Exception as e:
            self.client = None
            print(f"Error connecting to Space: {str(e)}")

    def detect(self, image_path):
        """
        Runs remote detection, draws annotations on the image, and returns 
        (list of detections, annotated_image_bytes).
        """
        if self.client is None:
            print("Gradio Client not initialized, skipping detection.")
            return [], None

        try:
            # Call the predict endpoint
            # Based on your app.py, the predict function takes an image and returns JSON
            result = self.client.predict(
                image=handle_file(image_path),
                api_name="/predict"
            )
            
            # The result from your app.py is boxes.data.tolist() which is a list of lists:
            # [x1, y1, x2, y2, confidence, class_id]
            detections_data = result if isinstance(result, list) else []
            
            detections = []
            img = cv2.imread(image_path)
            img_h, img_w, _ = img.shape

            for box_data in detections_data:
                if len(box_data) < 6: continue
                
                x1, y1, x2, y2, conf, cls_id = box_data
                
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
                    'confidence': float(conf),
                    'severity': severity,
                    'depth': depth,
                })
            
            # Convert annotated image back to bytes for Django
            success, buffer = cv2.imencode('.jpg', img)
            annotated_image_bytes = buffer.tobytes() if success else None
            
            return detections, annotated_image_bytes

        except Exception as e:
            print(f"Remote detection failed: {str(e)}")
            return [], None
