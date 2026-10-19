"""
Patient data model.

Represents a patient with their intake information including
demographics, symptoms, and extracted clinical data.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Patient:
    """Represents a patient entering the triage system."""

    name: str
    age: int
    symptoms: List[str]
    symptom_duration: str  # e.g., "3 days", "2 hours"
    contact: str = ""
    gender: str = "Unknown"

    # Auto-generated fields
    patient_id: str = field(default_factory=lambda: f"PAT-{uuid.uuid4().hex[:8].upper()}")
    created_at: datetime = field(default_factory=datetime.now)

    # Fields populated during triage
    priority_tier: Optional[str] = None
    severity_score: Optional[float] = None
    recommended_specialization: Optional[str] = None
    triage_notes: List[str] = field(default_factory=list)

    # Raw input preserved for audit
    raw_input: str = ""

    def to_dict(self) -> dict:
        """Serialize patient to dictionary for storage/transport."""
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "symptoms": self.symptoms,
            "symptom_duration": self.symptom_duration,
            "contact": self.contact,
            "priority_tier": self.priority_tier,
            "severity_score": self.severity_score,
            "recommended_specialization": self.recommended_specialization,
            "triage_notes": self.triage_notes,
            "raw_input": self.raw_input,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Patient:
        """Deserialize patient from dictionary."""
        patient = cls(
            name=data["name"],
            age=int(data["age"]),
            symptoms=data.get("symptoms", []),
            symptom_duration=data.get("symptom_duration", ""),
            contact=data.get("contact", ""),
            gender=data.get("gender", "Unknown"),
        )
        patient.patient_id = data.get("patient_id", patient.patient_id)
        patient.priority_tier = data.get("priority_tier")
        patient.severity_score = data.get("severity_score")
        patient.recommended_specialization = data.get("recommended_specialization")
        patient.triage_notes = data.get("triage_notes", [])
        patient.raw_input = data.get("raw_input", "")
        return patient

    def __str__(self) -> str:
        priority = self.priority_tier or "Unassessed"
        return (
            f"Patient({self.patient_id}: {self.name}, Age={self.age}, "
            f"Priority={priority}, Symptoms={self.symptoms})"
        )
