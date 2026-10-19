# 🏥 Agentic Triage & Operations Coordinator (ATOC)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-76%20passed%20(100%25)-brightgreen.svg)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-81%25-green.svg)](tests/)
[![Architecture](https://img.shields.io/badge/architecture-4--Agent%20Pipeline-purple.svg)](#architecture)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#)

> **Autonomous multi-agent clinical triage, scheduling, and operations engine.**  
> Moving beyond passive conversational chatbots to an intelligent, automated backend hospital operations pipeline that parses patient inputs, researches clinical severity guidelines, matches clinic resources, and validates bookings without conflicts.

---

## 📑 Table of Contents

- [Problem Statement](#problem-statement)
- [System Architecture](#system-architecture)
- [Agent Roles & Responsibilities](#agent-roles--responsibilities)
- [Multi-Turn Conversational Clarification (Agentic Interview)](#multi-turn-conversational-clarification-agentic-interview)
- [Voice & Audio Intake (Speech-to-Text)](#voice--audio-intake-speech-to-text)
- [Clinical Triage Guidelines & Tiers](#clinical-triage-guidelines--tiers)
- [Evaluation Metrics & Performance](#evaluation-metrics--performance)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
  - [1. Automated Clinical Benchmark](#1-automated-clinical-benchmark)
  - [2. Interactive Clinical CLI](#2-interactive-clinical-cli)
  - [3. Single-Query Execution](#3-single-query-execution)
  - [4. Modern Web Dashboard & REST API](#4-modern-web-dashboard--rest-api)
- [REST API Reference](#rest-api-reference)
- [Testing & Quality Assurance](#testing--quality-assurance)

---

## 🚨 Problem Statement

Modern outpatient clinics and emergency departments face staggering patient volumes. Traditional front-desk triage suffers from:
1. **Inefficient Manual Intake**: Long registration queues, incomplete symptom capture, and lack of standardized data entry.
2. **Clinical Triage Errors**: Subtle emergency signs (e.g., atypical cardiac presentations or acute neurological stroke deficits) can be misidentified as routine issues.
3. **Scheduling Bottlenecks & Collisions**: Manual doctor assignment causes double-bookings, specialization mismatches, and severe delays for high-acuity patients.
4. **Lack of Verifiable Audit Trails**: Unrecorded triage decisions lead to medicolegal vulnerability and fragmented clinical accountability.

### 💡 The Solution

The **Agentic Triage & Operations Coordinator (ATOC)** solves this through a deterministic, four-agent collaborative pipeline. Each agent is specialized for a distinct role (**Planner**, **Research**, **Executor**, **Validator**), collaborating via a shared context bus and producing an immutable audit log.

---

## 🏛️ System Architecture

The pipeline executes sequentially with structured state handover and rollback protection:

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Patient / Nurse
    participant Intake as Intake Agent (Planner)
    participant Triage as Triage Agent (Research)
    participant Ops as Operations Agent (Executor)
    participant Critic as Critic Agent (Validator)
    participant DB as Mock Clinical DB

    Patient->>Intake: Natural language text or structured JSON
    Note over Intake: Extract entities (Age, Symptoms, Duration, Vitals)
    Intake->>Triage: Structured Patient Profile + Extraction Confidence
    Note over Triage: Cross-reference Medical Guidelines<br/>Check Red Flags & Apply Modifiers
    Triage->>Ops: Assigned Priority Tier + Recommended Specialization
    Ops->>DB: Query Available Doctors & Urgent Slot Capacity
    DB-->>Ops: Return Optimal Slot & Doctor Match
    Ops->>DB: Reserve Candidate Appointment
    Ops->>Critic: Tentative Appointment + Patient Context
    Note over Critic: Double-booking verification<br/>Congruence & Safety cross-check
    Critic->>DB: Finalize Confirmation
    Critic-->>Patient: Verified Appointment Slip & Triage Report
```

---

## 🤖 Agent Roles & Responsibilities

| Agent | Core Role | Design Pattern | Key Responsibilities |
| :--- | :--- | :--- | :--- |
| **Intake Agent** | **Planner** | Entity Extraction & Synthesizer | Parses free-text conversational input or structured payloads; identifies symptoms, age, duration, and demographics; computes an extraction confidence score; falls back safely on missing fields. |
| **Triage Agent** | **Research** | Rule-Based Knowledge Engine | Cross-references extracted symptoms against comprehensive clinical guidelines; triggers acute red-flag combination rules (FAST stroke, acute MI, anaphylaxis); factors in age and duration modifiers; calculates normalized severity score `[0.0, 1.0]`; assigns Manchester Triage priority tiers; selects optimal medical specialization. |
| **Operations Agent** | **Executor** | Resource Scheduler | Interacts with the thread-safe clinic database; filters doctors by target specialization and priority handling capability; matches slot urgency to triage priority; tracks physician daily patient loads; prevents capacity overruns. |
| **Critic Agent** | **Validator** | Safety & Quality Critic | Validates tentative bookings against double-booking collisions; confirms doctor specialization matches patient condition; ensures high-acuity patients receive appropriate immediate slots; synthesizes a human-readable confirmation summary and audit record. |

---

## 💬 Multi-Turn Conversational Clarification (Agentic Interview)

In real-world emergency and clinical workflows, patient descriptions are frequently ambiguous, incomplete, or missing critical triage markers. Rather than forcing a low-confidence guess or requiring nurses to re-type full histories, ATOC features an **Agentic Clarification Interview Engine**:

1. **Stateful Session Tracking (`TriageSessionManager`)**:
   - Each clinical interaction creates or resumes a thread-safe `TriageSession` (`SES-XXXXXXXX`).
   - Conversations preserve turn-by-turn utterances, extracted clinical entities, and partial triage state across multiple round-trips.

2. **Proactive Red-Flag Probing**:
   - When potentially life-threatening but unverified symptoms are mentioned in isolation, the Intake Agent automatically generates targeted clinical inquiries:
     - **Isolated Chest Pain**: Immediately checks for radiation to left arm/jaw, diaphoresis, or acute shortness of breath (Myocardial Infarction screening).
     - **Severe Headache**: Probes for neck stiffness, photo-phobia, and high fever (Bacterial Meningitis screening).
     - **Severe Abdominal Pain**: Screens for hematemesis, melena, and acute rebound tenderness.
     - **Missing Temporal Acuity**: Inquires whether symptoms began minutes, hours, or weeks ago to apply accurate clinical modifiers.
     - **Missing Age**: Prompts for patient age to evaluate pediatric or geriatric risk multipliers.

3. **Interactive Quick-Reply Options**:
   - The Intake Agent pairs questions with structured clinical options (e.g., `["Yes, radiating to left arm/jaw", "Yes, having difficulty breathing", "No, localized chest pain only"]`).
   - Available via both interactive CLI (numeric/text selection) and the web dashboard (one-click option chips).

4. **Pipeline Interruption & Resumption**:
   - When clarification is needed, the pipeline pauses after the Intake Agent (`needs_clarification: True`), avoiding premature database reservations.
   - When the patient responds, answers are merged with prior turns, and the pipeline resumes seamlessly through Triage, Operations, and Critic Agents.

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Patient / Nurse
    participant Coordinator as Orchestrator / Session Manager
    participant Intake as Intake Agent
    participant Pipeline as Triage & Ops & Critic

    Patient->>Coordinator: "I have sharp chest pain" [Turn 1]
    Coordinator->>Intake: Analyze input
    Intake->>Coordinator: Ambiguity detected (Potential MI red flag)
    Coordinator-->>Patient: "Does your chest pain radiate to arm or jaw, or cause breathing difficulty?"<br/>[Options: Yes radiating / Yes SOB / No localized]
    Note over Coordinator: Session paused (SES-B5C620D2)

    Patient->>Coordinator: "Yes, radiating to left arm for 20 minutes" [Turn 2]
    Coordinator->>Intake: Merge session context & re-extract
    Intake->>Coordinator: Confidence 1.0, Acute MI Red Flag Confirmed
    Coordinator->>Pipeline: Resume: Triage (RED) -> Ops (Cardiology 09:00) -> Critic (Confirmed)
    Coordinator-->>Patient: Emergency Appointment Confirmed (0 min wait)
```

---

## 🎙️ Voice & Audio Intake (Speech-to-Text)

To empower hands-free clinical dictation and rapid emergency triage, ATOC includes a comprehensive **Voice & Audio Intake Subsystem**:

1. **Browser-Native Dictation (Web Speech API)**:
   - One-click microphone toggle (`#btnVoiceInput`) utilizing continuous speech recognition (`webkitSpeechRecognition` / `SpeechRecognition`).
   - Real-time speech streaming directly into the patient intake console.
   - Visual pulsing recording indicator with dynamic CSS audio waveform bars.

2. **Backend Transcription & Audio Upload Engine (`/api/voice-transcribe`)**:
   - Supports file uploads (`.wav`, `.mp3`, `.ogg`, `.webm`) and base64 encoded audio payloads.
   - Clinical audio processing pipeline with timestamp tracking and signal length analysis.

3. **One-Touch Clinical Voice Presets**:
   - Embedded audio voice scenarios representing typical outpatient and emergency presentations:
     - 🚨 **Cardiac Emergency**: *"62-year-old male with crushing substernal chest pain radiating to the left arm and severe shortness of breath for 30 minutes"*
     - 🧠 **Acute Stroke Deficit**: *"71-year-old female presenting with sudden onset right-sided facial drooping and slurred speech starting 45 minutes ago"*
     - 👶 **Pediatric High Fever**: *"3-year-old boy with high continuous fever of 103 degrees Fahrenheit, persistent dry cough and extreme lethargy for 2 days"*
     - 🩺 **Routine Outpatient**: *"29-year-old software engineer experiencing mild itchy skin rash on forearms for 4 days"*

---

## 🩺 Clinical Triage Guidelines & Tiers

Adapted from the **Manchester Triage System (MTS)** and standard emergency department protocols:

| Tier | Label | Target Max Wait | Severity Score | Color Code | Clinical Action |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **RED** | **Emergency** | **Immediate (0 min)** | `0.80 – 1.00` | `#EF4444` | Immediate resuscitation or acute intervention. Bypasses regular queue. |
| **ORANGE** | **Very Urgent** | **15 minutes** | `0.60 – 0.79` | `#F97316` | Rapid clinical evaluation. High-risk presentation (acute chest pain, high pediatric fever). |
| **YELLOW** | **Urgent** | **60 minutes** | `0.40 – 0.59` | `#FBBF24` | Serious condition requiring diagnostic investigation and timely care. |
| **GREEN** | **Standard** | **120 minutes** | `0.20 – 0.39` | `#10B981` | Stable routine complaints (minor pain, sub-acute cough, rash). |
| **BLUE** | **Non-Urgent** | **240 minutes** | `0.00 – 0.19` | `#3B82F6` | Minor or chronic conditions eligible for general outpatient care. |

### 🚩 Red-Flag Combinations (Immediate Escalation to RED)
- `chest pain` + `shortness of breath` → Potential Myocardial Infarction / PE
- `facial drooping` + `slurred speech` / `numbness` → Potential Acute Ischemic Stroke (FAST)
- `severe headache` + `stiff neck` + `fever` → Potential Bacterial Meningitis
- `difficulty breathing` + `swelling of throat` → Acute Anaphylaxis / Airway Compromise
- `vomiting blood` + `dizziness` → Acute Upper GI Hemorrhage

### ⏱️ Modifiers Applied
- **Age Modifiers**: Infants (`1.40x`), Toddlers (`1.25x`), Elderly `75+` (`1.35x`), Seniors `60-74` (`1.20x`). Minors (`<18`) automatically route to **Pediatrics**.
- **Duration Modifiers**: Acute onset in minutes (`1.30x`), hours (`1.15x`), weeks (`0.90x`), chronic months (`0.85x`).

---

## 📊 Evaluation Metrics & Performance

The system was benchmarked against diverse real-world clinical presentations:

| Metric | Target | Result | Status |
| :--- | :---: | :---: | :---: |
| **Priority Concordance (Accuracy)** | ≥ 95% | **100.0%** (6/6 Test Battery) | ✅ Exceeded |
| **Red-Flag Recall / Sensitivity** | 100% | **100.0%** (Zero missed red flags) | ✅ Exceeded |
| **Double-Booking Collisions** | 0% | **0.0%** (100% conflict prevention) | ✅ Verified |
| **Average Pipeline Latency** | < 100 ms | **4.10 ms** | ⚡ Ultra-fast |
| **Auditability & Traceability** | 100% | **100.0%** (Per-step audit timestamps) | ✅ Complete |
| **Unit & Integration Test Pass Rate**| 100% | **76 / 76 passed (100%)** | ✅ Verified |

---

## 📂 Project Structure

```
FAAI/
├── agents/                       # Autonomous Agent implementations
│   ├── __init__.py
│   ├── base_agent.py            # BaseAgent abstract class & AgentResult contract
│   ├── intake_agent.py          # Intake Agent (Planner + Clarification Interview)
│   ├── triage_agent.py          # Triage Agent (Research role)
│   ├── operations_agent.py      # Operations Agent (Executor role)
│   └── critic_agent.py          # Critic Agent (Validator role)
├── config/                       # Configuration & settings
│   ├── __init__.py
│   ├── settings.py              # Application settings, thresholds, priority tiers
│   └── logging_config.py        # Centralized per-agent structured logging
├── data/                         # Clinical knowledge base & storage
│   ├── __init__.py
│   ├── medical_guidelines.py    # 40+ symptoms, red-flags, age/duration modifiers
│   └── mock_database.py         # Thread-safe Singleton DB (12 doctors, slots, CRUD)
├── models/                       # Domain data models
│   ├── __init__.py
│   ├── patient.py               # Patient entity model
│   ├── doctor.py                # Doctor entity model
│   └── appointment.py           # Appointment entity model & lifecycle status
├── orchestrator/                 # Pipeline orchestration
│   ├── __init__.py
│   ├── coordinator.py           # TriageCoordinator multi-agent pipeline controller
│   └── session_manager.py       # TriageSessionManager for multi-turn stateful chats
├── utils/                        # Parsing, validation & formatting helpers
│   ├── __init__.py
│   ├── nlp_parser.py            # Natural language regex symptom & age parser
│   ├── validators.py            # Clinical & scheduling safety validators
│   └── formatters.py            # Pretty-printed reports, ASCII cards & summaries
├── web/                          # Full-stack Web Dashboard
│   ├── __init__.py
│   ├── app.py                   # Flask server with REST API & Voice Transcribe endpoints
│   ├── static/
│   │   ├── css/style.css        # Dark-mode glassmorphic styling, waveforms & chips
│   │   └── js/main.js           # Web Speech API, clarification handler & live dashboard
│   └── templates/
│       └── index.html           # Modern responsive dashboard with Voice & Clarification UI
├── tests/                        # Comprehensive test suite (76 tests)
│   ├── test_conversational_intake.py # Multi-turn sessions & clarification tests
│   ├── test_intake_agent.py     # Free-text parsing & patient creation tests
│   ├── test_triage_agent.py     # Severity scoring, red-flags & modifiers tests
│   ├── test_operations_agent.py # Scheduling & capacity tests
│   ├── test_critic_agent.py     # Double-booking & cross-check tests
│   ├── test_orchestrator.py     # End-to-end pipeline coordination tests
│   ├── test_mock_database.py    # Concurrency, CRUD & slot management tests
│   └── test_web_app.py          # REST API, Voice & Multi-turn Web route integration tests
├── main.py                       # Unified CLI with interactive interview & benchmark
├── requirements.txt              # Production & test dependencies
└── README.md                     # System documentation
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9, 3.10, 3.11, 3.12, or 3.13
- Git

### Installation Steps

```bash
# Clone the repository
git clone https://github.com/CallMePREMx/Agentic-Triage-Operations-Coordinator.git
cd Agentic-Triage-Operations-Coordinator

# Create and activate a virtual environment (recommended)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Running the Application

`main.py` provides a versatile multi-mode CLI:

### 1. Automated Clinical Benchmark
Runs the complete battery of clinical cases, evaluating priority concordance, latency, and conflict prevention:
```bash
python main.py --benchmark
```

**Sample Output:**
```
+==============================================================================+
|   [+] AGENTIC TRIAGE & OPERATIONS COORDINATOR                                |
|   Autonomous Multi-Agent Clinical Workflow & Scheduling Engine v1.0.0         |
+==============================================================================+

===============================================================================================
Case ID        | Assigned Tier | Specialization     | Doctor & Slot              | Latency  | Status
-----------------------------------------------------------------------------------------------
CASE-01-RED    | RED           | Cardiology         | Dr. Priya Sharma (09:00)   | 5.5      | [MATCH]
CASE-02-ORANGE | ORANGE        | Gastroenterology   | Dr. Thomas Wright (09:00)  | 3.6      | [MATCH]
CASE-03-PEDIATRIC | ORANGE     | Pediatrics         | Dr. Robert Kim (09:00)     | 3.6      | [MATCH]
CASE-04-GREEN  | GREEN         | Orthopedics        | Dr. Elena Volkov (13:30)   | 4.1      | [MATCH]
CASE-05-BLUE   | GREEN         | Dermatology        | Dr. Lisa Nakamura (13:30)  | 4.1      | [MATCH]
CASE-06-STROKE | RED           | Neurology          | Dr. Michael Foster (09:00) | 3.8      | [MATCH]
===============================================================================================

Benchmark Summary:
  * Total Test Cases      : 6
  * Priority Concordance  : 6/6 (100.0%)
  * Average Pipeline Time : 4.10 ms
  * Conflict Prevention   : 100% (Zero double bookings detected)
  * Critic Agent Summary  : All bookings cross-validated
```

### 2. Interactive Clinical CLI
Run an interactive session where you can type patient notes or select preset cases:
```bash
python main.py --interactive
```

### 3. Single-Query Execution
Pass patient symptom description directly via the `--text` argument:
```bash
python main.py --text "64-year-old female with acute chest pain and shortness of breath for 30 minutes"
```

### 4. Modern Web Dashboard & REST API
Launch the interactive web application:
```bash
python main.py --web
# Or: python web/app.py
```
Open **`http://localhost:5000`** in any modern web browser to access the dashboard.

---

## 🌐 REST API Reference

The Flask application exposes a complete REST API:

### `POST /api/triage`
Executes the multi-agent triage pipeline. Supports both single-pass batch triage and multi-turn conversational interviews.

**Request (Natural Language / Conversational):**
```json
{
  "message": "I'm having sharp chest pain",
  "session_id": "SES-B5C620D2",
  "allow_clarification": true
}
```

**Response when Intake Agent detects ambiguity (`needs_clarification: true`):**
```json
{
  "request_id": "REQ-92506EDB",
  "success": false,
  "needs_clarification": true,
  "session_id": "SES-B5C620D2",
  "clarification_prompt": "Does the chest pain radiate to your left arm or jaw, or cause breathing difficulty?",
  "missing_fields": ["radiation_or_dyspnea", "symptom_duration", "age"],
  "quick_replies": [
    "Yes, radiating to left arm/jaw",
    "Yes, having difficulty breathing",
    "No, localized chest pain only"
  ],
  "turn_count": 1
}
```

**Follow-Up Turn / Resumption:**
```json
{
  "message": "Yes, radiating to left arm for 20 minutes, I am 58",
  "session_id": "SES-B5C620D2",
  "allow_clarification": true
}
```

**Full Pipeline Response (200 OK):**
```json
{
  "request_id": "REQ-71043653",
  "success": true,
  "elapsed_seconds": 0.005,
  "session_id": "SES-B5C620D2",
  "patient": {
    "patient_id": "PAT-7B8DE591",
    "name": "Marcus Aurelius",
    "age": 58,
    "symptoms": ["chest pain", "shortness of breath"],
    "symptom_duration": "30 minutes",
    "priority_tier": "RED",
    "severity_score": 1.0,
    "recommended_specialization": "Cardiology"
  },
  "appointment": {
    "appointment_id": "APT-46D9B4A8",
    "patient_id": "PAT-7B8DE591",
    "doctor_id": "DOC-003",
    "doctor_name": "Priya Sharma",
    "specialization": "Cardiology",
    "date": "2026-10-19",
    "time_slot": "09:00",
    "priority_tier": "RED",
    "status": "CONFIRMED",
    "validated_by_critic": true
  },
  "triage_report": "...",
  "confirmation_summary": "...",
  "audit_trail": [...]
}
```

### `POST /api/voice-transcribe`
Transcribes clinical voice audio files, base64 data, or returns simulated clinical scenarios.

**Request (Preset Scenario):**
```json
{
  "preset": "cardiac"
}
```
*Presets available: `"cardiac"`, `"stroke"`, `"pediatric"`, `"routine"`*

**Response (200 OK):**
```json
{
  "success": true,
  "transcript": "62-year-old male with crushing substernal chest pain radiating to the left arm and severe shortness of breath for 30 minutes",
  "duration_seconds": 3.8,
  "source": "preset:cardiac",
  "confidence": 0.98
}
```

### `GET /api/session/<session_id>`
Retrieves the state, turn history, and accumulated patient draft for an active conversation session.

### Other Endpoints
| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `GET` | `/api/doctors` | Retrieve list of all 12 doctors and real-time available slots |
| `GET` | `/api/appointments` | Retrieve all scheduled and confirmed appointments |
| `GET` | `/api/patients` | Retrieve list of registered patient profiles |
| `GET` | `/api/stats` | Hospital real-time operational capacity and utilization rates |
| `GET` | `/api/priority-tiers` | Manchester Triage tier definitions and wait time SLA |
| `GET` | `/api/agents` | Status and role metadata for the 4 autonomous agents |
| `POST` | `/api/reset` | Reset the in-memory database to clean initial state |

---

## 🧪 Testing & Quality Assurance

The project includes an exhaustive test suite covering all agents, utilities, the mock database, concurrency, multi-turn interviews, and web APIs:

```bash
# Run all 76 tests
pytest

# Run tests with detailed coverage report
pytest --cov=. tests/
```

### Test Coverage Highlights:
- **`test_conversational_intake.py`**: Stateful session management, red-flag interview question generation, multi-turn context accumulation, interview resolution, and bypass flags.
- **`test_intake_agent.py`**: Free-text parsing, complex names, age units, duration normalization, missing field fallbacks.
- **`test_triage_agent.py`**: Manchester tier thresholds, multi-symptom weights, red-flag triggers, age & duration modifiers, pediatric routing.
- **`test_operations_agent.py`**: Doctor filtering, urgency slot sorting, capacity limit enforcement, fallback strategies.
- **`test_critic_agent.py`**: Double-booking detection, specialization mismatches, priority congruence, confirmation slip generation.
- **`test_orchestrator.py`**: Sequential pipeline flow, partial failure handling, audit trail generation.
- **`test_mock_database.py`**: Concurrency safety, slot booking & release, CSV export, statistics calculation.
- **`test_web_app.py`**: Flask REST endpoints, voice transcription, session fetching, multi-turn interview APIs, and dashboard HTML rendering.

---

## ⚖️ License & Medical Disclaimer

This project is released under the **MIT License**.

> **⚠️ Medical Disclaimer**: This software is designed for academic demonstration, evaluation, and operational prototyping purposes. While built using clinical guidelines inspired by the Manchester Triage System, it is not a certified medical device and should not be used as the sole basis for clinical diagnostic or emergency treatment decisions without licensed clinical oversight.
