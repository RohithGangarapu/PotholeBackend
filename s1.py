# test_mjpeg.py
import requests, time, cv2, numpy as np

URL = "http://10.64.6.250:5000/stream"

def mjpeg_frames(url, timeout=10, chunk_size=1024):
    while True:
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                buf = b''
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    buf += chunk
                    while True:
                        start = buf.find(b'\xff\xd8')
                        end = buf.find(b'\xff\xd9', start + 2) if start != -1 else -1
                        if start != -1 and end != -1:
                            jpg = buf[start:end+2]
                            buf = buf[end+2:]
                            frame = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
                            yield frame
                        else:
                            # keep buffer bounded
                            if len(buf) > 1_000_000:
                                buf = buf[-65536:]
                            break
        except Exception as e:
            print("MJPEG error:", e)
            time.sleep(2)
            continue

if __name__ == "__main__":
    for i, frame in enumerate(mjpeg_frames(URL), 1):
        if frame is None:
            print("frame is None")
            continue
        print("frame", i, "shape:", frame.shape)
        cv2.imshow("frame", frame)
        if cv2.waitKey(1) & 0xFF == ord('q') or i >= 300:
            break
    cv2.destroyAllWindows()