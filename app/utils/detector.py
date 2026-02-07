import cv2
import numpy as np
import os
import requests
import json
import time
import uuid

class PotholeDetector:
    def __init__(self):
        self.space_id = "RohithGangarapu/PotholeYoloV8-NEW"
        self.space_url = "https://rohithgangarapu-potholeyolov8-new.hf.space"
        self.upload_url = f"{self.space_url}/gradio_api/upload"
        self.call_url = f"{self.space_url}/gradio_api/call/predict"

    def _upload_file(self, file_path):
        try:
            img = cv2.imread(file_path)
            if img is None:
                return None

            # 🔥 Resize before upload (CRITICAL)
            img = cv2.resize(img, (640, 480))

            _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])

            files = {
                "files": ("frame.jpg", buffer.tobytes(), "image/jpeg")
            }

            response = requests.post(
                self.upload_url,
                files=files,
                timeout=60   # ⬆ increased
            )

            if response.status_code == 200:
                return response.json()[0]

        except Exception as e:
            print(f"File upload failed: {e}")

        return None

    def detect(self, image_path):
        """
        Runs remote detection using raw HTTP/SSE requests (bypassing gradio_client).
        Returns (list of detections, annotated_image_bytes).
        """
        try:
            # 1. Upload file if it's local
            print(f"Preparing image for remote detection...")
            remote_path = self._upload_file(image_path)
            if not remote_path:
                print("Failed to upload image to remote API.")
                return [], None

            # 2. Create Inference Task
            print("Creating inference task on Hugging Face...")
            payload = {"data": [{"path": remote_path}]}
            response = requests.post(self.call_url, json=payload, timeout=15)
            
            if response.status_code != 200:
                print(f"Failed to create task: {response.text}")
                return [], None

            event_id = response.json().get("event_id")
            result_url = f"{self.call_url}/{event_id}"

            # 3. Listen for SSE Result
            print(f"Waiting for AI result (Event: {event_id})...")
            detections_data = []
            
            # We poll until we get the 'complete' event or timeout
            with requests.get(result_url, stream=True, timeout=60) as r:
                current_event = None
                for line in r.iter_lines():
                    if not line: continue
                    decoded = line.decode('utf-8')
                    
                    if decoded.startswith("event:"):
                        current_event = decoded.replace("event:", "").strip()
                    elif decoded.startswith("data:"):
                        data_str = decoded.replace("data:", "").strip()
                        
                        if current_event == "complete":
                            data = json.loads(data_str)
                            if isinstance(data, list) and len(data) >= 2:
                                detections_data = data[1] # [annotated_image, detections_list]
                            break
                        elif current_event == "error":
                            print(f"Remote AI Error: {data_str}")
                            return [], None

            # 4. Local Annotation
            print(f"Processing {len(detections_data)} remote detections...")
            img = cv2.imread(image_path)
            if img is None:
                return [], None
            
            img_h, img_w, _ = img.shape
            detections = []

            for box_data in detections_data:
                # Expecting [x1, y1, x2, y2, confidence, class_id]
                if not isinstance(box_data, list) or len(box_data) < 6:
                    continue
                
                x1, y1, x2, y2, conf, cls_id = box_data
                
                # Heuristics for depth & severity
                rel_area = ((x2 - x1) * (y2 - y1)) / (img_h * img_w)
                depth = round(rel_area * 50, 2)
                
                if depth > 15:
                    severity, color = 'high', (0, 0, 255)
                elif depth > 5:
                    severity, color = 'medium', (0, 165, 255)
                else:
                    severity, color = 'low', (0, 255, 0)
                
                # Draw on image
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 3)
                cv2.putText(img, f"Pothole: {depth}cm", (int(x1), int(y1) - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                
                detections.append({
                    'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    'confidence': float(conf),
                    'severity': severity,
                    'depth': float(depth),
                })

            # Encode annotated image
            success, buffer = cv2.imencode('.jpg', img)
            annotated_image_bytes = buffer.tobytes() if success else None
            
            return detections, annotated_image_bytes

        except Exception as e:
            print(f"Detector error: {str(e)}")
            return [], None
