<div align="center">

# 🚀 OPERIX
### Multi-Department Industrial Operations, Custom Constraints & Safety Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18%2B-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-8.2-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Computer%20Vision-00FFFF?style=for-the-badge)](https://ultralytics.com/)

*Enterprise-grade Computer Vision, Deterministic Rule Evaluation, Workforce Analytics, and Bilingual LLM/RAG Intelligence — built on existing RTSP CCTV & Thermal camera networks.*

[📚 API Docs](./docs/frontend-integration/README.md) • [🔌 OpenAPI Spec](./docs/frontend-integration/openapi.json) • [✅ Frontend Checklist](./docs/frontend-integration/frontend-integration-checklist.md)

</div>

---

## 📌 Executive Summary

**Operix** transforms standard industrial **RTSP CCTV and Thermal cameras** into a unified, multi-tenant safety and operations intelligence platform — eliminating the need for proprietary hardware upgrades.

| Capability | Technology | Outcome |
| :--- | :--- | :--- |
| 🛡️ **Safety & PPE Compliance** | `YOLOv8` + `ByteTrack` + Pose/Fatigue + Thermal | Real-time detection of PPE violations, falls, fatigue, fire/smoke & restricted zone intrusions |
| 📐 **No-Code Polygon Rules** | Visual Canvas + Deterministic Policy Engine | Department-specific spatial zones & configurable thresholds without touching code |
| ⏳ **Workforce Analytics** | Canonical SQLAlchemy + RLS Scoped Queries | Net working hours, attendance activity, resolution KPIs & camera coverage gaps |
| 🔐 **Incident Evidence** | Factory-Scoped Storage + `SHA-256` | Tamper-evident snapshots & clips with cryptographic integrity verification |
| 🤖 **Bilingual RAG & AI Actions** | Bilingual (`AR`/`EN`) RAG + `AIActionService` | Grounded operational Q&A, source citations & RBAC-protected remediation actions |
| 📄 **Automated Reports** | PDF & Excel Export Engine | Tenant-isolated Workforce, Incident, Camera Coverage & Safety reports |

---

## 🏗️ 3-Tier Event-Driven Architecture

```mermaid
flowchart TB
    subgraph T1["Tier 1 · Computer Vision & AI Perception Layer (50%)"]
        direction LR
        CV1["🎥 Mahmoud Abdelghany<br/>RTSP Ingestion · YOLOv8 + ByteTrack<br/>PPE & Worker Tracking"]
        CV2["🦺 Mohamed Shahin<br/>Fall Detection · Fatigue Analysis<br/>Restricted Zone Logic"]
        CV3["🔥 Mohamed Salah<br/>Thermal & Fire/Smoke AI<br/>Cross-Camera Re-ID · DB"]
    end

    BUS(["⚡ Unified JSON Event Stream<br/>(Camera_ID · Track_ID · Event · Coords · Timestamp)"])

    subgraph T2["Tier 2 · Backend, Rule Engine & Data Science Layer (33%)"]
        direction LR
        BE["⚙️ Seif Sameh<br/>FastAPI + WebSockets · Polygon Rule Engine<br/>Evidence Recording · Multi-Channel Alerts"]
        AI["🧠 Abdallah Waleed<br/>Workforce Analytics · Net Hours<br/>LLM/RAG Assistant · AI Actions · Reports"]
    end

    API(["🔌 REST API (/api/v1) & Real-Time WebSockets"])

    subgraph T3["Tier 3 · Presentation & User Interface Layer (17%)"]
        FE["🖥️ Toka Medhat<br/>React.js + Tailwind Dashboard · Live Streams<br/>Visual Polygon Canvas · Charts · Assistant & Reports UI"]
    end

    T1 --> BUS --> T2 --> API --> T3
```

---

## 🧩 Core Platform Modules

### 1️⃣ No-Code Polygon Rule Builder & Constraints Engine
Administrators draw custom spatial polygon zones on camera views and bind department-level rules (`ppe_violation`, `restricted_zone_intrusion`, `fall`, `fire`, `smoke`, `temperature_anomaly`) with configurable confidence and duration thresholds.

### 2️⃣ Workforce Analytics & Net Working Time
Reconstructs net productive hours, worker activity, incident resolution efficiency, and camera uptime / unobserved monitoring gaps per factory:

$$
T_{net} = T_{presence} - T_{idle} - T_{approved\_breaks}
$$

### 3️⃣ Incident Evidence & Cryptographic Integrity
Stores event snapshots and clips in factory-isolated paths with `SHA-256` checksum verification (`POST /api/v1/evidence/{id}/verify-integrity`) and strict path-traversal containment.

### 4️⃣ Bilingual LLM/RAG Assistant & Agentic AI Actions
Supervisors and managers query safety rules and operational logs in **Arabic or English** (`POST /api/v1/assistant/ask`) with grounded citations, conversation ownership enforcement, and RBAC-validated remediation execution (`POST /api/v1/assistant/actions/execute`).

### 5️⃣ Automated Reports Generation
Generates factory-scoped **PDF** and **Excel** reports across Workforce, Incident, Camera Coverage, and Comprehensive Safety domains (`POST /api/v1/reports/generate`).

---

## 👥 Team Architecture & Role Distribution

<table>
  <thead>
    <tr>
      <th>Tier</th>
      <th>Member</th>
      <th>Role</th>
      <th>Core Responsibilities</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="3" align="center"><b>Tier 1</b><br/>CV &amp; AI Perception<br/><code>50%</code></td>
      <td><b>Mahmoud Abdelghany</b></td>
      <td>CV/IoT Pipeline Engineer</td>
      <td>RTSP Live Stream Ingestion, YOLOv8 + ByteTrack Detection &amp; Tracking, PPE Detection, System Integration.</td>
    </tr>
    <tr>
      <td><b>Mohamed Shahin</b></td>
      <td>Computer Vision &amp; Safety AI Engineer</td>
      <td>Fall Detection (Pose/Motion), Fatigue Analysis (Eye Closure, Yawning, Head Pose), Restricted Zone Logic, Dataset Curation.</td>
    </tr>
    <tr>
      <td><b>Mohamed Salah</b></td>
      <td>CV, Thermal AI &amp; Database Engineer</td>
      <td>Fire &amp; Smoke Detection, Thermal Sensor/Camera Analytics, Cross-Camera Re-ID, PostgreSQL Database Management.</td>
    </tr>
    <tr>
      <td rowspan="2" align="center"><b>Tier 2</b><br/>Backend &amp; Data Science<br/><code>33%</code></td>
      <td><b>Abdallah Waleed</b></td>
      <td>Team Lead, Data Science &amp; AI Assistant Engineer</td>
      <td>Workforce Analytics &amp; Net Working Hours, LLM/RAG AI Assistant, Agentic AI Actions, Automated Reports (PDF/Excel), Evidence Integration.</td>
    </tr>
    <tr>
      <td><b>Seif Sameh</b></td>
      <td>Backend &amp; Rule Engine Engineer</td>
      <td>FastAPI REST &amp; WebSockets Server, No-Code Polygon Rule Builder &amp; Evaluator, Evidence Recording, Multi-Channel Alerts (Telegram/SMS/Email).</td>
    </tr>
    <tr>
      <td align="center"><b>Tier 3</b><br/>Frontend UI/UX<br/><code>17%</code></td>
      <td><b>Toka Medhat</b></td>
      <td>Frontend &amp; UI/UX Engineer</td>
      <td>Interactive React.js Dashboard, Live Streams &amp; Alert Popups, Visual Polygon Zone Canvas, Analytics Charts, Evidence, Reports &amp; Assistant UI.</td>
    </tr>
  </tbody>
</table>

---

## 🛠️ Quick Start & API Documentation

| Resource | Link |
| :--- | :--- |
| **Frontend Integration Hub** | [`docs/frontend-integration/README.md`](./docs/frontend-integration/README.md) |
| **OpenAPI 3.x Specification** | [`docs/frontend-integration/openapi.json`](./docs/frontend-integration/openapi.json) (`32` paths · `21` Frontend endpoints) |
| **JS Fetch Client Examples** | [`docs/frontend-integration/frontend-api-examples.js`](./docs/frontend-integration/frontend-api-examples.js) |
| **Frontend Integration Checklist** | [`docs/frontend-integration/frontend-integration-checklist.md`](./docs/frontend-integration/frontend-integration-checklist.md) |

<details>
<summary><b>⚡ Local Development Run Commands</b></summary>

```bash
# 1. Backend (from backend/)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

# 2. Frontend (from Frontend/)
npm install
npm run dev
```

</details>

---

## 🗓️ Two-Semester Roadmap

```mermaid
gantt
    dateFormat  YYYY-MM-DD
    title Operix Development Roadmap

    section Semester 1 (MVP Core)
    PostgreSQL Schema & Auth Foundation (Salah & Seif)                :done, s1_1, 2026-10-01, 30d
    YOLO, PPE & Fall/Fatigue Models (Mahmoud, Shahin, Salah)          :done, s1_2, 2026-10-01, 30d
    React UI Setup & Dashboard (Toka)                                 :done, s1_3, 2026-10-01, 30d
    FastAPI, WebSockets & Rule Evaluator (Seif)                       :done, s1_4, after s1_1, 30d
    Workforce Analytics & Evidence Modules (Abdallah)                 :done, s1_5, after s1_2, 30d

    section Semester 2 (AI Integration & Production Readiness)
    LLM/RAG Assistant, AI Actions & Reports (Abdallah)                :done, s2_1, 2026-11-01, 25d
    Backend-AI Synchronization & Security Hardening (Seif & Abdallah) :done, s2_2, after s2_1, 10d
    Frontend-Backend Full API Integration (Toka)                      :active, s2_3, after s2_2, 20d
    End-to-End CV Hardware & Stress Testing (All)                     :s2_4, after s2_3, 25d
```
