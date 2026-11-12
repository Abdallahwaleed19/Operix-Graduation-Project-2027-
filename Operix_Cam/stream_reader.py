"""
stream_reader.py — Operix Threaded RTSP Frame Grabber
======================================================
CameraStream opens the RTSP feed in a background daemon thread so that
cv2.VideoCapture.read() never blocks the main (display) thread.

Key design decisions
---------------------
* **Lock-free double-buffer**: The background thread always writes the latest
  decoded frame into `self._frame`; the main thread reads it whenever it is
  ready.  A threading.Lock guards the swap so reads never see a torn write.

* **Automatic reconnection**: If the stream drops (read() returns False, or
  the capture handle becomes invalid), the thread waits RECONNECT_DELAY
  seconds then tries to re-open the RTSP URL — no manual restart needed.

* **Daemon thread**: Marked as daemon so the process exits cleanly even if
  the thread is blocked on a network read.

Usage
-----
    cam = CameraStream(rtsp_url)
    cam.start()
    frame = cam.get_frame()   # returns None until first frame arrives
    cam.stop()
"""

import time
import threading
import logging

import cv2

from config import RTSP_URL, RECONNECT_DELAY

logger = logging.getLogger(__name__)


class CameraStream:
    """
    Non-blocking, auto-reconnecting RTSP camera reader.

    Parameters
    ----------
    rtsp_url : str
        Full RTSP URL, e.g. ``rtsp://192.168.1.9:554/md0_0``.
    reconnect_delay : int
        Seconds to wait between reconnection attempts (default: from config).
    """

    def __init__(self, rtsp_url: str = RTSP_URL,
                 reconnect_delay: int = RECONNECT_DELAY) -> None:
        self._url             = rtsp_url
        self._reconnect_delay = reconnect_delay

        self._cap:    cv2.VideoCapture | None = None
        self._frame:  cv2.typing.MatLike | None = None
        self._lock    = threading.Lock()

        self._running    = False
        self._connected  = False
        self._thread:    threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> "CameraStream":
        """Start the background capture thread. Returns self for chaining."""
        self._running = True
        self._thread  = threading.Thread(
            target=self._capture_loop, name="CameraStream", daemon=True
        )
        self._thread.start()
        logger.info("[CameraStream] Background thread started.")
        return self

    def stop(self) -> None:
        """Signal the background thread to stop and release resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._release_cap()
        logger.info("[CameraStream] Stopped and resources released.")

    def get_frame(self) -> "cv2.typing.MatLike | None":
        """
        Return the most recent decoded frame, or ``None`` if none is
        available yet.  Thread-safe; never blocks.
        """
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    @property
    def is_connected(self) -> bool:
        """True while the RTSP stream is open and delivering frames."""
        return self._connected

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open_capture(self) -> bool:
        """
        Attempt to open the RTSP stream. Returns True on success.
        cv2.CAP_FFMPEG is explicit so OpenCV always uses the FFmpeg backend
        (which honours the OPENCV_FFMPEG_CAPTURE_OPTIONS env var set in
        config.py to force TCP transport).
        """
        self._release_cap()
        logger.info("[CameraStream] Connecting to %s …", self._url)
        cap = cv2.VideoCapture(self._url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            self._cap       = cap
            self._connected = True
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            logger.info(
                "[CameraStream] Connected — %dx%d @ %.1f FPS", w, h, fps
            )
            return True
        cap.release()
        logger.warning("[CameraStream] Could not open stream.")
        return False

    def _release_cap(self) -> None:
        """Safely release the VideoCapture handle."""
        if self._cap is not None:
            self._cap.release()
            self._cap       = None
            self._connected = False

    def _capture_loop(self) -> None:
        """
        Background thread: continuously read frames and handle reconnections.
        """
        while self._running:
            # --- (Re)connect if needed -----------------------------------
            if not self._connected:
                if not self._open_capture():
                    logger.info(
                        "[CameraStream] Retrying in %ds …",
                        self._reconnect_delay,
                    )
                    time.sleep(self._reconnect_delay)
                    continue

            # --- Read one frame ------------------------------------------
            ret, frame = self._cap.read()

            if not ret or frame is None:
                logger.warning(
                    "[CameraStream] Stream read failed — will reconnect."
                )
                self._release_cap()
                time.sleep(self._reconnect_delay)
                continue

            # --- Store the latest frame (lock-protected) -----------------
            with self._lock:
                self._frame = frame

        # Thread is exiting — ensure clean release
        self._release_cap()
