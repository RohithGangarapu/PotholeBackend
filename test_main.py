import os
import sys
import cv2
import time
import uuid
import threading
import numpy as np
import re
import requests

# ================= DJANGO SETUP =================
PROJECT_ROOT = "C:\\Final Year Project\\pothole_backend\\PotholeBackend"   # 🔴 CHANGE THIS
sys.path.append(PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")  # 🔴 CHANGE THIS

import django
django.setup()

from app.models import Pothole, IOTDevice,User
from django.core.files.base import ContentFile

from app.utils.detector import PotholeDetector

# ================= ESP GPS =================
ESP_ROOT_URL = "http://10.120.93.250/"
last_gps = {"lat": None, "lng": None}
gps_lock = threading.Lock()

# ================= DB CONSTANTS =================
DEVICE_ID = 1
USER_ID = 1

device = IOTDevice.objects.get(id=DEVICE_ID)
user = User.objects.get(id=USER_ID)

# ================= GPS THREAD =================
def gps_worker():
    global last_gps

    while True:
        try:
            r = requests.get("http://10.120.93.227/gps", timeout=2)

            if r.status_code == 200:
                data = r.json()   # 👈 THIS is the key line


                if data.get("status") == "OK":
                    lat = data.get("lat")
                    lng = data.get("lng")

                    if lat is not None and lng is not None:
                        with gps_lock:
                            last_gps = {"lat": lat, "lng": lng}

        except Exception as e:
            print("GPS error:", e)

        time.sleep(1)


# ================= SAVE POTHOLE =================
def save_pothole(detection, annotated_bytes=None):
    with gps_lock:
        lat = last_gps.get("lat")
        lng = last_gps.get("lng")

    if lat is None or lng is None:
        print("⚠ GPS not fixed yet, skipping pothole save")
        return

    pothole = Pothole(
        device=device,
        user=user,
        depth=detection["depth"],
        severity=detection["severity"],
        latitude=lat,
        longitude=lng,
        status="unresolved"
    )

    if annotated_bytes:
        image_name = f"pothole_{uuid.uuid4()}.jpg"
        pothole.image.save(
            image_name,
            ContentFile(annotated_bytes),
            save=False
        )

    pothole.save()
    print(f"✅ Pothole saved [{pothole.severity}] {pothole.depth}cm @ {lat}, {lng}")

# ================= STREAM CONFIG =================
MJPEG_STREAM_URL = "http://10.120.93.250/stream"
FRAME_SAVE_DIR = "temp_frames"
DETECT_EVERY_N_SECONDS = 5

os.makedirs(FRAME_SAVE_DIR, exist_ok=True)

detector = PotholeDetector()

latest_frame = None
last_detect_time = 0
lock = threading.Lock()

# ================= DETECTION THREAD =================
def detection_worker():
    global latest_frame, last_detect_time

    while True:
        time.sleep(0.1)

        if latest_frame is None:
            continue

        if time.time() - last_detect_time < DETECT_EVERY_N_SECONDS:
            continue

        with lock:
            frame = latest_frame.copy()

        frame_path = os.path.join(FRAME_SAVE_DIR, f"{uuid.uuid4()}.jpg")
        cv2.imwrite(frame_path, frame)

        print("[AI] Running pothole detection...")
        detections, annotated_bytes = detector.detect(frame_path)

        if annotated_bytes:
            annotated = cv2.imdecode(
                np.frombuffer(annotated_bytes, np.uint8),
                cv2.IMREAD_COLOR
            )
            if annotated is not None:
                cv2.imshow("Pothole Detection", annotated)

        if detections:
            print("Detections:", detections)
            for det in detections:
                save_pothole(det, annotated_bytes)

        os.remove(frame_path)
        last_detect_time = time.time()

# ================= MAIN =================
if __name__ == "__main__":

    # Start background threads
    threading.Thread(target=gps_worker, daemon=True).start()
    threading.Thread(target=detection_worker, daemon=True).start()

    print("Opening MJPEG stream...")
    cap = cv2.VideoCapture(MJPEG_STREAM_URL)

    if not cap.isOpened():
        raise RuntimeError("❌ Cannot open MJPEG stream")

    print("✅ Stream started")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("⚠ Stream dropped. Reconnecting...")
            cap.release()
            time.sleep(1)
            cap = cv2.VideoCapture(MJPEG_STREAM_URL)
            continue

        with lock:
            latest_frame = frame

        cv2.imshow("Live Stream", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Stopped cleanly")
