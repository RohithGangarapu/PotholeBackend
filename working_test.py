import cv2
import time
import uuid
import os
import threading
import numpy as np


from app.utils.detector import PotholeDetector


# ================= CONFIG =================
MJPEG_STREAM_URL = "http://10.120.93.250/stream"
FRAME_SAVE_DIR = "temp_frames"
DETECT_EVERY_N_SECONDS = 5   # run AI every X seconds

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

        frame_id = str(uuid.uuid4())
        frame_path = os.path.join(FRAME_SAVE_DIR, f"{frame_id}.jpg")
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

        os.remove(frame_path)
        last_detect_time = time.time()


# ================= MAIN =================
print("Opening MJPEG stream...")
cap = cv2.VideoCapture(MJPEG_STREAM_URL)

if not cap.isOpened():
    raise RuntimeError("❌ Cannot open MJPEG stream")

# Start AI thread
threading.Thread(target=detection_worker, daemon=True).start()

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

# ================= CLEANUP =================
cap.release()
cv2.destroyAllWindows()
print("Stopped cleanly")
