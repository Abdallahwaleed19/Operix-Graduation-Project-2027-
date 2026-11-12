# 📋 Operix — Session Dev Log
**Date:** Thursday, 12 November 2026  
**Session Time:** ~14:33 → 15:05 (Cairo / EET, UTC+2)  
**Developer:** Abdallah Waleed  
**Project:** Operix — Industrial Monitoring System  
**University:** Menoufia National University · Faculty of Computers & AI · Level 4 · Graduation Project 2026–2027

---

## 🎯 Session Objective

Build and verify the **base RTSP camera ingestion pipeline** for Operix — a clean, production-ready Python module that streams live video from the lab's IP camera with no latency buffering, automatic reconnection, and a live FPS/status overlay.

> No AI models, no recording — strict stream verification only.

---

## 📷 Hardware Verified

| Property | Value |
|---|---|
| **Camera Model** | Skyworth LC2308 (I63D4H2-AWT) |
| **RTSP URL** | `rtsp://192.168.1.9:554/md0_0` |
| **Native Resolution** | 2304 × 1296 |
| **Native FPS** | ~19.9 FPS (H.264) |
| **Transport** | TCP (forced via FFmpeg env var — prevents Wi-Fi packet loss) |

---

## 🗂️ Project Structure Created

```
Operix/
└── Operix_Cam/
    ├── .env                ← Camera URL & display config (network-switchable)
    ├── .gitignore          ← Keeps .env out of version control
    ├── config.py           ← Loads .env, sets OPENCV_FFMPEG TCP transport
    ├── stream_reader.py    ← Threaded, auto-reconnecting RTSP frame grabber
    ├── main.py             ← Entry point: live display + FPS/status overlay
    ├── requirements.txt    ← Dependencies list
    └── .venv/              ← Python virtual environment (all deps installed)
```

**Full path:**
```
D:\Menoufia National University 2026-2027\
  Faculty_of_Computers_&_Artificial_Intelligence\
    Level 4\Graduated Project 2026-2027\Operix\Operix_Cam\
```

---

## 🔧 Files Built

### `.env`
Stores all runtime configuration — no hardcoded values in source files.
```env
RTSP_URL=rtsp://192.168.1.9:554/md0_0
DISPLAY_WIDTH=1280
DISPLAY_HEIGHT=720
RECONNECT_DELAY=3
```
> To switch networks for the graduation demo: edit only this file.

---

### `config.py`
- Loads `.env` via `python-dotenv`
- Sets `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp` as a process-level env var **before** any OpenCV import
- Exports typed constants: `RTSP_URL`, `DISPLAY_WIDTH`, `DISPLAY_HEIGHT`, `WINDOW_TITLE`, `RECONNECT_DELAY`

---

### `stream_reader.py` — `CameraStream` class
| Feature | Implementation |
|---|---|
| **Non-blocking reads** | Daemon background thread continuously grabs frames |
| **Lock-free display** | `threading.Lock` guards frame swap; main thread never waits on network I/O |
| **Auto-reconnect** | On `read()` failure → releases handle → sleeps `RECONNECT_DELAY`s → retries |
| **Backend** | Explicit `cv2.CAP_FFMPEG` to honour TCP transport env var |
| **API** | `start()` · `stop()` · `get_frame()` · `is_connected` property |

---

### `main.py`
- Initialises `CameraStream` and starts background thread
- Resizes frames to `1280×720` with `cv2.INTER_LINEAR`
- Draws **shadowed overlay** (readable on any background):
  - Top-left: `FPS: XX.X` + resolution label
  - Top-right: **`LIVE`** (green) or **`RECONNECTING…`** (red) badge
  - Bottom-left: hotkey hint
- Shows a dark placeholder while awaiting the first frame
- **Graceful exit** on `Q`, `ESC`, or `Ctrl+C` → `cam.stop()` + `cv2.destroyAllWindows()`

---

### `requirements.txt`
```
opencv-python
python-dotenv
numpy
```

---

## 📦 Environment Setup

```powershell
# Virtual environment created
python -m venv .venv

# Dependencies installed (exit code 0 ✓)
.\.venv\Scripts\pip install -r requirements.txt
```

**Installed versions:**
| Package | Version |
|---|---|
| `opencv-python` | 5.0.0.93 |
| `python-dotenv` | 1.2.4 |
| `numpy` | 2.5.4 |

---

## ✅ Live Test Result

```
14:37:02  INFO  Operix — RTSP Camera Verification Module
14:37:02  INFO  Stream : rtsp://192.168.1.9:554/md0_0
14:37:02  INFO  [CameraStream] Connecting to rtsp://192.168.1.9:554/md0_0 …
14:37:04  INFO  [CameraStream] Connected — 2304x1296 @ 19.9 FPS  ✓
```

- **Stream opened successfully** in ~2 seconds
- **Window displayed** at 1280×720 with live FPS counter and green LIVE badge
- **TCP transport** active — no packet loss or frame tearing observed
- **Exit** via `Q`/`ESC` cleaned up all resources gracefully

---

## ▶️ Run Command (for future reference)

```powershell
cd "d:\Menoufia National University 2026-2027\Faculty_of_Computers_&_Artificial_Intelligence\Level 4\Graduated Project 2026-2027\Operix\Operix_Cam"
.\.venv\Scripts\python main.py
```

---

## 🔜 Next Steps (suggested)

- [ ] Add **object detection / YOLO inference** layer on top of `get_frame()`
- [ ] Add **video recording** module (triggered recording on detection events)
- [ ] Integrate with **Operix backend API** to push detection events
- [ ] Add **multi-camera** support (multiple `CameraStream` instances)
- [ ] Package as a **Windows service** for 24/7 unattended operation

---

*Document generated: 12 November 2026 · Operix Graduation Project*
