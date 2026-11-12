"""
main.py — Operix Live Camera Feed Entry Point
=============================================
Initialises CameraStream, displays the live feed resized to the configured
resolution, and overlays real-time FPS and connection status.

Controls
--------
  q  or  ESC  — quit cleanly
"""

import logging
import sys
import time

import cv2

from config import DISPLAY_WIDTH, DISPLAY_HEIGHT, WINDOW_TITLE, RTSP_URL
from stream_reader import CameraStream

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Overlay helpers
# ---------------------------------------------------------------------------

_FONT       = cv2.FONT_HERSHEY_SIMPLEX
_GREEN      = (0, 220, 0)
_RED        = (0, 50, 220)
_WHITE      = (255, 255, 255)
_SHADOW     = (30, 30, 30)
_SCALE_BIG  = 0.65
_SCALE_SML  = 0.55
_THICKNESS  = 2
_LINE       = cv2.LINE_AA


def _put_text_shadowed(
    img,
    text: str,
    origin: tuple[int, int],
    scale: float,
    color: tuple[int, int, int],
    thickness: int = _THICKNESS,
) -> None:
    """Draw text with a 1-pixel dark shadow for readability on any background."""
    ox, oy = origin
    cv2.putText(img, text, (ox + 1, oy + 1), _FONT, scale, _SHADOW, thickness, _LINE)
    cv2.putText(img, text, (ox, oy),          _FONT, scale, color,   thickness, _LINE)


def _draw_overlay(
    frame,
    fps: float,
    is_connected: bool,
    display_w: int,
    display_h: int,
) -> None:
    """Render FPS counter and connection status onto the frame in-place."""
    # ---- FPS counter (top-left) ----------------------------------------
    _put_text_shadowed(
        frame,
        f"FPS: {fps:5.1f}",
        (12, 32),
        _SCALE_BIG,
        _WHITE,
    )

    # ---- Stream resolution (top-left, below FPS) -----------------------
    _put_text_shadowed(
        frame,
        f"{display_w}x{display_h}",
        (12, 60),
        _SCALE_SML,
        _WHITE,
    )

    # ---- Connection badge (top-right) ----------------------------------
    if is_connected:
        badge_text  = "LIVE"
        badge_color = _GREEN
    else:
        badge_text  = "RECONNECTING..."
        badge_color = _RED

    (tw, th), _ = cv2.getTextSize(badge_text, _FONT, _SCALE_BIG, _THICKNESS)
    bx = display_w - tw - 14
    _put_text_shadowed(frame, badge_text, (bx, 32), _SCALE_BIG, badge_color)

    # ---- Hotkey hint (bottom-left) -------------------------------------
    _put_text_shadowed(
        frame,
        "Press  Q / ESC  to quit",
        (12, display_h - 12),
        _SCALE_SML,
        _WHITE,
        thickness=1,
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run() -> None:
    logger.info("=" * 60)
    logger.info("  Operix — RTSP Camera Verification Module")
    logger.info("  Camera : Skyworth LC2308 (I63D4H2-AWT)")
    logger.info("  Stream : %s", RTSP_URL)
    logger.info("  Display: %dx%d", DISPLAY_WIDTH, DISPLAY_HEIGHT)
    logger.info("=" * 60)

    cam = CameraStream()
    cam.start()

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_TITLE, DISPLAY_WIDTH, DISPLAY_HEIGHT)

    # FPS calculation state
    frame_count  = 0
    fps_start    = time.perf_counter()
    display_fps  = 0.0

    # Placeholder frame shown while waiting for the first real frame
    placeholder = _make_placeholder()

    logger.info("Window open. Press Q or ESC to quit.")

    try:
        while True:
            # ---- Grab latest frame from the background thread ----------
            frame = cam.get_frame()

            if frame is None:
                # Still waiting for first frame — show placeholder
                display_frame = placeholder.copy()
            else:
                display_frame = cv2.resize(
                    frame,
                    (DISPLAY_WIDTH, DISPLAY_HEIGHT),
                    interpolation=cv2.INTER_LINEAR,
                )
                # Update FPS every second
                frame_count += 1
                elapsed = time.perf_counter() - fps_start
                if elapsed >= 1.0:
                    display_fps  = frame_count / elapsed
                    frame_count  = 0
                    fps_start    = time.perf_counter()

            # ---- Draw overlay ------------------------------------------
            _draw_overlay(
                display_frame,
                display_fps,
                cam.is_connected,
                DISPLAY_WIDTH,
                DISPLAY_HEIGHT,
            )

            cv2.imshow(WINDOW_TITLE, display_frame)

            # ---- Key handling ------------------------------------------
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):   # 27 = ESC
                logger.info("Exit key pressed.")
                break

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received — shutting down.")

    finally:
        logger.info("Releasing resources …")
        cam.stop()
        cv2.destroyAllWindows()
        logger.info("Done. Goodbye.")


def _make_placeholder():
    """Return a dark grey placeholder frame with a waiting message."""
    img = __import__("numpy").zeros(
        (DISPLAY_HEIGHT, DISPLAY_WIDTH, 3), dtype="uint8"
    )
    img[:] = (30, 30, 30)
    msg   = "Connecting to camera..."
    (tw, th), _ = cv2.getTextSize(msg, _FONT, 0.9, 2)
    cx = (DISPLAY_WIDTH  - tw) // 2
    cy = (DISPLAY_HEIGHT + th) // 2
    cv2.putText(img, msg, (cx, cy), _FONT, 0.9, (160, 160, 160), 2, _LINE)
    return img


if __name__ == "__main__":
    run()
