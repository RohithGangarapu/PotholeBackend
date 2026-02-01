import io
import logging
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import cv2
import requests

from .frame_queue import add_frame_processing_task, frame_queue, init_frame_queue

logger = logging.getLogger(__name__)

# Global dictionary to track active streams
_active_streams: Dict[str, "VideoStreamProcessor"] = {}
_stream_lock = threading.Lock()


def _is_probably_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https", "rtsp", "rtmp"}


def _resolve_video_source(video_source: str) -> str:
    """Resolve local relative paths (e.g. sample/sample.mp4) to an absolute path."""
    video_source = (video_source or "").strip()
    if _is_probably_url(video_source):
        return video_source

    p = Path(video_source)
    if p.is_absolute() and p.exists():
        return str(p)

    # Project root is the Django project directory (where manage.py is)
    project_root = Path(__file__).resolve().parents[2]
    candidate = project_root / video_source
    if candidate.exists():
        return str(candidate)

    # Fallback: return as-is (OpenCV may still handle it if CWD matches)
    return video_source


@dataclass
class StreamStats:
    frames_processed: int = 0  # sampled frames (one per interval)
    frames_sent: int = 0       # successful POSTs to detection endpoint
    frames_failed: int = 0     # failed POSTs / encode failures
    frames_dropped: int = 0    # dropped due to queue backpressure
    last_frame_time: Optional[float] = None   # last successful cap.read() wall time
    last_sample_time: Optional[float] = None  # last sampled frame wall time
    last_error: Optional[str] = None


class VideoStreamProcessor:
    def __init__(
        self,
        stream_id: str,
        video_source: str,
        detection_api_url: str,
        frame_interval: int = 30,
        device_id: Optional[int] = None,
        user_id: Optional[int] = None,
        request_timeout_s: int = 60,
        max_queue_size: int = 50,
    ):
        self.stream_id = stream_id
        self.video_source = _resolve_video_source(video_source)
        self.detection_api_url = detection_api_url
        self.frame_interval = int(frame_interval)
        self.device_id = device_id
        self.user_id = user_id
        self.request_timeout_s = request_timeout_s
        self.max_queue_size = max_queue_size

        self.is_running = False
        self.connection_active = False

        self._thread: Optional[threading.Thread] = None
        self._stats = StreamStats()
        self._stats_lock = threading.Lock()

    def start(self) -> bool:
        if self.is_running:
            return False

        # Ensure background workers are running
        init_frame_queue()

        # Fail fast if OpenCV can't open the source.
        # This avoids returning "success" from the API while the background thread immediately errors.
        test_cap = cv2.VideoCapture(self.video_source)
        try:
            if not test_cap.isOpened():
                self.connection_active = False
                self._set_error(f"Failed to open video source: {self.video_source}")
                logger.error(self._stats.last_error)
                return False
        finally:
            try:
                test_cap.release()
            except Exception:
                pass

        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> bool:
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        return True

    def get_status(self) -> Dict[str, Any]:
        with self._stats_lock:
            s = self._stats
            return {
                "stream_id": self.stream_id,
                "is_running": self.is_running,
                "connection_active": self.connection_active,
                "video_source": self.video_source,
                "frame_interval": self.frame_interval,
                "frames_processed": s.frames_processed,
                "frames_sent": s.frames_sent,
                "frames_failed": s.frames_failed,
                "frames_dropped": s.frames_dropped,
                "last_frame_time": s.last_frame_time,
                "last_sample_time": s.last_sample_time,
                "last_error": s.last_error,
                "device_id": self.device_id,
                "user_id": self.user_id,
            }

    def _set_error(self, msg: str) -> None:
        with self._stats_lock:
            self._stats.last_error = msg

    def _capture_loop(self) -> None:
        """Main capture loop that tries OpenCV first, then falls back to MJPEG if needed."""
        # If it's an HTTP/HTTPS URL, it's very likely an MJPEG stream for these IoT devices
        is_http = self.video_source.startswith(("http://", "https://"))
        
        if is_http:
            logger.info("Stream %s: Attempting MJPEG capture for HTTP source", self.stream_id)
            if self._mjpeg_capture_loop():
                logger.info("Stream %s: MJPEG capture loop exited normally", self.stream_id)
                return
            logger.warning("Stream %s: MJPEG capture failed, falling back to OpenCV", self.stream_id)

        # Fallback to OpenCV (handles local files, RTSP, and some HTTP MJPEG)
        self._opencv_capture_loop()

    def _opencv_capture_loop(self) -> None:
        cap: Optional[cv2.VideoCapture] = None
        try:
            cap = cv2.VideoCapture(self.video_source)
            if not cap.isOpened():
                self.connection_active = False
                self._set_error(f"Failed to open video source: {self.video_source}")
                logger.error(self._stats.last_error)
                return

            # Reduce latency for some streaming sources (best-effort)
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            self.connection_active = True

            is_local_file = (not _is_probably_url(self.video_source)) and Path(self.video_source).exists()
            last_sample_wall = 0.0
            last_sample_msec: Optional[float] = None

            while self.is_running:
                ret, frame = cap.read()
                now = time.time()

                if not ret:
                    self.connection_active = False
                    self._set_error("Stream ended or error reading frame")
                    logger.warning("Stream %s read failed; source=%s", self.stream_id, self.video_source)

                    # For local files: we are done.
                    if is_local_file:
                        break

                    # For live sources: attempt a simple reconnect loop.
                    time.sleep(2)
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = cv2.VideoCapture(self.video_source)
                    if not cap.isOpened():
                        continue
                    self.connection_active = True
                    continue

                with self._stats_lock:
                    self._stats.last_frame_time = now

                # Decide whether to sample based on video time (for files) or wall-clock.
                should_sample = False
                if is_local_file:
                    pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                    if pos_msec and pos_msec > 0:
                        if last_sample_msec is None or (pos_msec - last_sample_msec) >= self.frame_interval * 1000:
                            should_sample = True
                            last_sample_msec = pos_msec
                    else:
                        # Fallback
                        if (now - last_sample_wall) >= self.frame_interval:
                            should_sample = True
                            last_sample_wall = now
                else:
                    if (now - last_sample_wall) >= self.frame_interval:
                        should_sample = True
                        last_sample_wall = now

                if should_sample:
                    self._enqueue_detection(frame, now)

                # Yield a tiny bit (cap.read() may already block, but this prevents a hot loop on files)
                time.sleep(0.001)

        except Exception as e:
            self.connection_active = False
            self._set_error(str(e))
            logger.exception("Error in OpenCV capture loop for %s", self.stream_id)
        finally:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass

    def _mjpeg_capture_loop(self) -> bool:
        """Capture loop specifically for multipart/x-mixed-replace MJPEG streams."""
        try:
            resp = requests.get(self.video_source, stream=True, timeout=10)
            if resp.status_code != 200:
                self._set_error(f"HTTP {resp.status_code} from {self.video_source}")
                return False

            # Some ESP32-CAM firmware doesn't send the multipart header correctly, 
            # so we'll try to parse it anyway if the status is 200.
            content_type = resp.headers.get('Content-Type', '').lower()
            if 'multipart' not in content_type and 'image/jpeg' not in content_type:
                logger.debug("Stream %s: Unusual Content-Type '%s', attempting parse anyway", self.stream_id, content_type)

            self.connection_active = True
            last_sample_wall = 0.0
            byte_stream = bytes()
            
            # Max buffer size to prevent memory leaks if markers are missing (10MB)
            MAX_BUFFER_SIZE = 10 * 1024 * 1024

            # Iterate over the response stream
            for chunk in resp.iter_content(chunk_size=4096):
                if not self.is_running:
                    break

                byte_stream += chunk
                
                # Check for buffer overflow
                if len(byte_stream) > MAX_BUFFER_SIZE:
                    logger.warning("Stream %s: MJPEG buffer overflow, clearing", self.stream_id)
                    byte_stream = bytes()
                    continue

                # Search for JPEG start and end markers
                a = byte_stream.find(b'\xff\xd8') # JPEG start
                b = byte_stream.find(b'\xff\xd9') # JPEG end
                
                if a != -1 and b != -1 and b > a:
                    jpg_data = byte_stream[a:b+2]
                    # Keep the remainder
                    byte_stream = byte_stream[b+2:]
                    
                    now = time.time()
                    with self._stats_lock:
                        self._stats.last_frame_time = now

                    if (now - last_sample_wall) >= self.frame_interval:
                        # Convert to OpenCV frame for processing
                        frame = cv2.imdecode(cv2.frombuffer(jpg_data, dtype=cv2.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            self._enqueue_detection(frame, now)
                            last_sample_wall = now
                        else:
                            logger.warning("Stream %s: Failed to decode JPEG frame", self.stream_id)

            return True

        except Exception as e:
            msg = f"MJPEG capture error: {str(e)}"
            self._set_error(msg)
            logger.debug("Stream %s: %s", self.stream_id, msg)
            return False
        finally:
            self.connection_active = False

    def _enqueue_detection(self, frame, sample_time: float) -> None:
        # Backpressure: if queue is too large, drop.
        try:
            qsize = frame_queue.task_queue.qsize()
        except Exception:
            qsize = 0

        if qsize >= self.max_queue_size:
            with self._stats_lock:
                self._stats.frames_dropped += 1
                self._stats.last_sample_time = sample_time
            return

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            with self._stats_lock:
                self._stats.frames_failed += 1
                self._stats.last_sample_time = sample_time
            return

        jpg_bytes = buffer.tobytes()

        with self._stats_lock:
            self._stats.frames_processed += 1
            frame_number = self._stats.frames_processed
            self._stats.last_sample_time = sample_time

        task_id = f"{self.stream_id}:{frame_number}:{uuid.uuid4().hex[:8]}"
        add_frame_processing_task(task_id, self._post_frame_to_detection, jpg_bytes, frame_number)

    def _post_frame_to_detection(self, jpg_bytes: bytes, frame_number: int) -> Dict[str, Any]:
        """Runs in background worker threads."""
        try:
            files = {
                "photo": (f"{self.stream_id}_{frame_number}.jpg", io.BytesIO(jpg_bytes), "image/jpeg")
            }
            data: Dict[str, str] = {}
            if self.device_id is not None:
                data["deviceId"] = str(self.device_id)
            if self.user_id is not None:
                data["userId"] = str(self.user_id)

            resp = requests.post(
                self.detection_api_url,
                files=files,
                data=data,
                timeout=self.request_timeout_s,
            )
            resp.raise_for_status()

            try:
                payload = resp.json()
            except Exception:
                payload = {"raw": resp.text}

            with self._stats_lock:
                self._stats.frames_sent += 1

            return payload

        except Exception as e:
            with self._stats_lock:
                self._stats.frames_failed += 1
                self._stats.last_error = str(e)
            raise


def start_video_stream(
    stream_id: str,
    video_source: str,
    detection_api_url: str,
    frame_interval: int = 30,
    device_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """Start a video stream processing worker in the background.

    Returns (success, error_message).
    """
    with _stream_lock:
        if stream_id in _active_streams:
            msg = f"Stream {stream_id} is already running"
            logger.warning(msg)
            return False, msg

        processor = VideoStreamProcessor(
            stream_id=stream_id,
            video_source=video_source,
            detection_api_url=detection_api_url,
            frame_interval=frame_interval,
            device_id=device_id,
            user_id=user_id,
        )

        if processor.start():
            _active_streams[stream_id] = processor
            return True, None

        # processor.start() will set last_error.
        err = processor.get_status().get("last_error") or "Failed to start stream"
        return False, err


def stop_video_stream(stream_id: str) -> bool:
    with _stream_lock:
        processor = _active_streams.get(stream_id)
        if not processor:
            return False

        processor.stop()
        del _active_streams[stream_id]
        return True


def get_stream_status(stream_id: str) -> Optional[Dict[str, Any]]:
    with _stream_lock:
        processor = _active_streams.get(stream_id)
        if not processor:
            return None
        return processor.get_status()


def get_all_streams_status() -> Dict[str, Any]:
    with _stream_lock:
        return {stream_id: processor.get_status() for stream_id, processor in _active_streams.items()}
