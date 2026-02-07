import cv2
import numpy as np
import requests
import time
import uuid
import os

from app.utils.detector import PotholeDetector

# ================= CONFIG =================
MJPEG_STREAM_URL = "http://10.64.6.250/stream"   # <-- replace if needed
FRAME_SAVE_DIR = "temp_frames"
DETECT_EVERY_N_FRAMES = 15      # run AI every N frames
TIMEOUT = 10

os.makedirs(FRAME_SAVE_DIR, exist_ok=True)

# ================= INIT =================
detector = PotholeDetector()

print("Connecting to MJPEG stream...")
stream = requests.get(MJPEG_STREAM_URL, stream=True, timeout=TIMEOUT)

if stream.status_code != 200:
    raise RuntimeError("Failed to connect to MJPEG stream")

bytes_buffer = b""
frame_count = 0

print("Stream connected. Starting detection...")

# ================= STREAM LOOP =================
for chunk in stream.iter_content(chunk_size=1024):
    bytes_buffer += chunk

    start = bytes_buffer.find(b'\xff\xd8')  # JPEG start
    end = bytes_buffer.find(b'\xff\xd9')    # JPEG end

    if start != -1 and end != -1 and end > start:
        jpg = bytes_buffer[start:end+2]
        bytes_buffer = bytes_buffer[end+2:]

        # Decode frame
        frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            continue

        frame_count += 1

        # Show raw stream
        cv2.imshow("Live Stream", frame)

        # ================= RUN DETECTION =================
        if frame_count % DETECT_EVERY_N_FRAMES == 0:
            frame_id = str(uuid.uuid4())
            frame_path = os.path.join(FRAME_SAVE_DIR, f"{frame_id}.jpg")

            cv2.imwrite(frame_path, frame)

            print(f"[INFO] Running detection on frame {frame_count}")
            detections, annotated_bytes = detector.detect(frame_path)

            if annotated_bytes:
                annotated = cv2.imdecode(
                    np.frombuffer(annotated_bytes, np.uint8),
                    cv2.IMREAD_COLOR
                )

                if annotated is not None:
                    cv2.imshow("Pothole Detection", annotated)

            if detections:
                print("Detections:")
                for d in detections:
                    print(d)

            os.remove(frame_path)

        # Exit key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# ================= CLEANUP =================
stream.close()
cv2.destroyAllWindows()
print("Stopped.")
