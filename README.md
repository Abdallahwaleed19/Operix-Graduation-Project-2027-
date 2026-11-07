# 🚀 OPERIX

### Multi-Department Industrial Operations, Custom Constraints & Safety Intelligence Platform

---

## 📌 Executive Summary

**Operix** is an enterprise-grade Computer Vision and AI Intelligence platform designed for manufacturing plants and industrial facilities. Instead of requiring costly proprietary camera upgrades, Operix integrates directly with existing **RTSP CCTV networks**.

By combining state-of-the-art Object Detection ($YOLOv8/v9$), Multi-Object Tracking ($ByteTrack / DeepSORT$), and Pose Estimation ($MediaPipe / OpenPose$), Operix delivers continuous visibility into:

* 🛡️ **PPE & Danger Zone Safety Compliance**
* ⏳ **Net Working Time & Smart Break Tracking**
* 🗺️ **Spatial Density Foot-Traffic Heatmaps**
* 🤖 **Natural Language Operations Assistant (LLM RAG)**

---

## 🏗️ System Architecture

Operix uses an event-driven architecture that completely decouples video stream ingestion, perception analysis, business logic evaluation, and user presentation layers.

[ CCTV / RTSP Streams ] ──► [ RTSP Ingestion Service ] ──► [ Bounded Message Queue ]
│
┌────────────────────────────────────────────────────────────────────┘
▼
[ Perception Workers ]
├─► YOLOv8 / YOLOv9 (People & PPE Detection)
├─► ByteTrack / DeepSORT (Tracking & Identity Continuity)
├─► MediaPipe / OpenPose (Pose Estimation & Conflict Analysis)
└─► Heatmap Aggregator (Spatial Density Coordinates)
│
▼
[ Department Constraints & Policy Evaluator ]
│
├──► [ PostgreSQL DB ] (Persisted Events, Timesheets & Evidence Clips)
└──► [ FastAPI (REST + WebSockets) ] ──► [ React.js + Tailwind Dashboard ]
▲
│
[ LLM Operations Assistant ]


---

## 🧩 Key Platform Modules

### 1️⃣ Department-Specific Constraints Engine
Administrators draw custom spatial polygon zones on camera views and assign department-specific operating rules:
* **Welding Zone:** Requires Hard Hat + Safety Vest. Max idle limit: 15 minutes.
* **Warehouse Zone:** Requires Safety Vest only. Restricted entry hours enforced.

### 2️⃣ Net Working Time & Smart Break Tracking
Reconstructs net productive hours per worker shift, accounting for unobserved gaps and camera occlusions:

$$
T_{net} = T_{presence} - T_{idle} - T_{approved\_breaks}
$$

### 3️⃣ Spatial Density & Foot-Traffic Heatmaps
Calculates real-time Kernel Density Estimation (KDE) overlays over factory floor plans to highlight congestion spots, dwell times, and safety violation hotspots.

### 4️⃣ LLM Operations Assistant
Authorized managers can ask natural-language questions (e.g., *"Show me all unapproved breaks in Line 2 yesterday"*). The assistant queries structured PostgreSQL logs and provides verifiable event snapshots and evidence links.

---

## 👥 Project Team & Work Breakdown Structure (WBS)

The project development is distributed across **6 core roles**:

| Member | Role | Core Technical Responsibilities |
| :--- | :--- | :--- |
| **Abdallah Waleed** | **Lead AI & Vision Engineer** | YOLOv8/v9 Detection Pipeline, ByteTrack/DeepSORT Tracking, Heatmap Engine. |
| **Seif Sameh** | **AI & Action Recognition** | MediaPipe/OpenPose Analysis, Constraints Evaluator Engine, Net Hours Algorithm. |
| **Mohamed Shaheen** | **Backend Architect** | FastAPI (REST & WebSockets), RTSP Stream Ingestion, PostgreSQL & Evidence Storage. |
| **Toka Medhat** | **Frontend UI/UX Developer** | React.js & Tailwind Dashboard, Interactive Polygon Tool, Heatmap Overlay Layer. |
| **Mohamed Salah** | **Data Analytics & LLM Specialist** | Operix LLM Operations Assistant (RAG), Precision/Recall Metrics, Timesheets & KPIs. |
| **Mahmoud Abdelghany** | **DevOps & System Integration** | End-to-End System Integration, Camera RTSP Hardware Testing, Stress Testing & Docker. |

---

## 🗓️ Two-Semester Roadmap

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    title Operix Development Roadmap

    section Semester 1 (MVP Core)
    FastAPI & Infrastructure Setup (Shaheen & Mahmoud)   :active, s1_1, 2026-10-01, 30d
    YOLO Object & PPE Training (Abdallah & Seif)        :active, s1_2, 2026-10-01, 30d
    React UI Setup & Dashboard (Toka)                   :active, s1_3, 2026-10-01, 30d
    Dataset & Schema Design (Salah)                     :active, s1_4, 2026-10-01, 30d
    ByteTrack & Polygon Engine (Abdallah & Seif)        :s1_5, after s1_2, 30d
    WebSockets & Evidence Retention (Shaheen & Toka)    :s1_6, after s1_1, 30d
    Net Hours Algorithm & S1 Demo (Seif & Mahmoud)      :s1_7, after s1_5, 30d

    section Semester 2 (Advanced SaaS Readiness)
    Heatmap Analytics Engine (Abdallah & Toka)          :s2_1, 2027-02-01, 30d
    Pose Estimation & LLM Assistant (Seif & Salah)      :s2_2, 2027-02-01, 30d
    Unobserved Gap Handling & Reports (Shaheen & Salah) :s2_3, after s2_1, 30d
    Stress Testing & Final Defense (Mahmoud & All)       :s2_4, after s2_3, 30d
