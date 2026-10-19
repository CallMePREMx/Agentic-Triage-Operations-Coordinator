"""
Appointment data model.

Represents a booked appointment linking a patient to a doctor at a specific time.
Tracks status through its lifecycle: PENDING → CONFIRMED → COMPLETED / CANCELLED.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AppointmentStatus(Enum):
    """Lifecycle states for an appointment."""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class Appointment:
    """Represents a scheduled appointment in the system."""

    patient_id: str
    patient_name: str
    doctor_id: str
    doctor_name: str
    specialization: str
    time_slot: str
    priority_tier: str
    date: str  # YYYY-MM-DD

    # Auto-generated
    appointment_id: str = field(
        default_factory=lambda: f"APT-{uuid.uuid4().hex[:8].upper()}"
    )
    status: AppointmentStatus = AppointmentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)

    # Validation metadata
    validated_by_critic: bool = False
    validation_notes: list = field(default_factory=list)
    confirmation_summary: Optional[str] = None

    def confirm(self) -> None:
        """Mark the appointment as confirmed after critic validation."""
        self.status = AppointmentStatus.CONFIRMED
        self.validated_by_critic = True

    def cancel(self, reason: str = "") -> None:
        """Cancel the appointment."""
        self.status = AppointmentStatus.CANCELLED
        if reason:
            self.validation_notes.append(f"Cancelled: {reason}")

    def to_dict(self) -> dict:
        """Serialize appointment to dictionary."""
        return {
            "appointment_id": self.appointment_id,
            "patient_id": self.patient_id,
            "patient_name": self.patient_name,
            "doctor_id": self.doctor_id,
            "doctor_name": self.doctor_name,
            "specialization": self.specialization,
            "time_slot": self.time_slot,
            "priority_tier": self.priority_tier,
            "date": self.date,
            "status": self.status.value,
            "validated_by_critic": self.validated_by_critic,
            "validation_notes": self.validation_notes,
            "confirmation_summary": self.confirmation_summary,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Appointment:
        """Deserialize appointment from dictionary."""
        appt = cls(
            patient_id=data["patient_id"],
            patient_name=data["patient_name"],
            doctor_id=data["doctor_id"],
            doctor_name=data["doctor_name"],
            specialization=data["specialization"],
            time_slot=data["time_slot"],
            priority_tier=data["priority_tier"],
            date=data["date"],
        )
        appt.appointment_id = data.get("appointment_id", appt.appointment_id)
        appt.status = AppointmentStatus(data.get("status", "PENDING"))
        appt.validated_by_critic = data.get("validated_by_critic", False)
        appt.validation_notes = data.get("validation_notes", [])
        appt.confirmation_summary = data.get("confirmation_summary")
        return appt

    def __str__(self) -> str:
        return (
            f"Appointment({self.appointment_id}: {self.patient_name} → "
            f"Dr. {self.doctor_name} @ {self.time_slot} on {self.date}, "
            f"Priority={self.priority_tier}, Status={self.status.value})"
        )
