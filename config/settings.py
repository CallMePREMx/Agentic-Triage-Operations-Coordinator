"""
Global configuration settings for the Agentic Triage & Operations Coordinator.

Centralizes all configurable parameters: priority tiers, time slots,
specialization mappings, and application-wide constants.
"""

import os
from pathlib import Path

# ─── Project Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
CSV_DIR = DATA_DIR / "csv"

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)

# ─── Priority Tiers ──────────────────────────────────────────────────────────
# Each tier has: label, color code, max wait time (minutes), description
PRIORITY_TIERS = {
    "RED": {
        "label": "Emergency",
        "level": 1,
        "color": "#DC2626",
        "max_wait_minutes": 0,
        "description": "Life-threatening condition requiring immediate attention.",
    },
    "ORANGE": {
        "label": "Urgent",
        "level": 2,
        "color": "#EA580C",
        "max_wait_minutes": 15,
        "description": "Serious condition requiring prompt medical care.",
    },
    "YELLOW": {
        "label": "Semi-Urgent",
        "level": 3,
        "color": "#CA8A04",
        "max_wait_minutes": 60,
        "description": "Moderate condition that needs attention within an hour.",
    },
    "GREEN": {
        "label": "Routine",
        "level": 4,
        "color": "#16A34A",
        "max_wait_minutes": 240,
        "description": "Non-urgent condition suitable for routine scheduling.",
    },
    "BLUE": {
        "label": "Follow-Up",
        "level": 5,
        "color": "#2563EB",
        "max_wait_minutes": 1440,
        "description": "Follow-up or minor concern, can be scheduled next available.",
    },
}

# ─── Doctor Specializations ──────────────────────────────────────────────────
SPECIALIZATIONS = [
    "General Medicine",
    "Emergency Medicine",
    "Cardiology",
    "Neurology",
    "Orthopedics",
    "Pediatrics",
    "Dermatology",
    "ENT",
    "Gastroenterology",
    "Pulmonology",
]

# ─── Time Slot Configuration ─────────────────────────────────────────────────
WORKING_HOURS_START = 8   # 8:00 AM
WORKING_HOURS_END = 20    # 8:00 PM
SLOT_DURATION_MINUTES = 30

# ─── Application Settings ────────────────────────────────────────────────────
APP_NAME = "Agentic Triage & Operations Coordinator"
APP_VERSION = "1.0.0"
DEBUG_MODE = os.environ.get("ATOC_DEBUG", "false").lower() == "true"
WEB_HOST = os.environ.get("ATOC_HOST", "127.0.0.1")
WEB_PORT = int(os.environ.get("ATOC_PORT", "5000"))

# ─── Agent Configuration ─────────────────────────────────────────────────────
AGENT_CONFIG = {
    "intake": {
        "name": "Intake Agent",
        "role": "Planner",
        "description": "Parses user input to extract structured patient data.",
    },
    "triage": {
        "name": "Triage Agent",
        "role": "Research",
        "description": "Cross-references symptoms against medical guidelines for priority assignment.",
    },
    "operations": {
        "name": "Operations Agent",
        "role": "Executor",
        "description": "Finds available doctor slots matching priority tier.",
    },
    "critic": {
        "name": "Critic Agent",
        "role": "Validator",
        "description": "Validates bookings, prevents conflicts, and generates confirmations.",
    },
}
