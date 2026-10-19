"""
Doctor data model.

Represents a doctor with their specialization and available time slots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Doctor:
    """Represents a doctor with availability in the system."""

    doctor_id: str
    name: str
    specialization: str
    available_slots: List[str] = field(default_factory=list)  # e.g., ["09:00", "09:30"]
    handles_priority: List[str] = field(default_factory=list)  # e.g., ["RED", "ORANGE"]
    max_patients_per_day: int = 20
    current_patient_count: int = 0

    @property
    def is_available(self) -> bool:
        """Check if the doctor has any open slots and hasn't hit patient cap."""
        return (
            len(self.available_slots) > 0
            and self.current_patient_count < self.max_patients_per_day
        )

    def book_slot(self, slot: str) -> bool:
        """
        Remove a slot from availability and increment patient count.

        Args:
            slot: Time slot string (e.g., "09:00").

        Returns:
            True if slot was booked successfully, False otherwise.
        """
        if slot in self.available_slots:
            self.available_slots.remove(slot)
            self.current_patient_count += 1
            return True
        return False

    def release_slot(self, slot: str) -> None:
        """Release a previously booked slot back to availability."""
        if slot not in self.available_slots:
            self.available_slots.append(slot)
            self.available_slots.sort()
            self.current_patient_count = max(0, self.current_patient_count - 1)

    def to_dict(self) -> dict:
        """Serialize doctor to dictionary."""
        return {
            "doctor_id": self.doctor_id,
            "name": self.name,
            "specialization": self.specialization,
            "available_slots": self.available_slots,
            "handles_priority": self.handles_priority,
            "max_patients_per_day": self.max_patients_per_day,
            "current_patient_count": self.current_patient_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Doctor:
        """Deserialize doctor from dictionary."""
        return cls(
            doctor_id=data["doctor_id"],
            name=data["name"],
            specialization=data["specialization"],
            available_slots=data.get("available_slots", []),
            handles_priority=data.get("handles_priority", []),
            max_patients_per_day=data.get("max_patients_per_day", 20),
            current_patient_count=data.get("current_patient_count", 0),
        )

    def __str__(self) -> str:
        slot_count = len(self.available_slots)
        return (
            f"Dr. {self.name} ({self.specialization}) — "
            f"{slot_count} slots available, "
            f"handles: {', '.join(self.handles_priority)}"
        )
