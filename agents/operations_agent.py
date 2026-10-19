"""
Operations Agent (Executor Role).

Interacts with the mock database to find an available doctor slot
that matches the patient's priority tier and recommended specialization.
Handles slot selection strategy and creates a pending appointment.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentResult, BaseAgent
from data.mock_database import MockDatabase
from models.appointment import Appointment
from models.doctor import Doctor
from models.patient import Patient


class OperationsAgent(BaseAgent):
    """
    Operations Agent — the third agent in the pipeline.

    Responsibilities:
    1. Query the database for available doctors matching the priority
       tier and recommended specialization.
    2. If no specialist is available, fall back to broader matching.
    3. Select the best doctor-slot combination.
    4. Create a PENDING appointment in the database.
    """

    def __init__(self):
        super().__init__(
            name="OperationsAgent",
            role="Executor",
            description="Finds available doctor slots matching priority tier.",
        )
        self.db = MockDatabase()

    def process(self, input_data: Any, context: Dict) -> AgentResult:
        """
        Find a doctor and create a pending appointment.

        Args:
            input_data: Triaged Patient object.
            context: Shared pipeline context.

        Returns:
            AgentResult with Appointment object as data.
        """
        if not isinstance(input_data, Patient):
            return AgentResult(
                success=False,
                errors=["OperationsAgent expected a Patient object."],
            )

        patient = input_data
        warnings = []

        if not patient.priority_tier:
            return AgentResult(
                success=False,
                errors=["Patient has no priority tier assigned. Triage must run first."],
            )

        self.logger.info(
            "Finding appointment for %s (Priority: %s, Specialization: %s)",
            patient.patient_id, patient.priority_tier,
            patient.recommended_specialization,
        )

        # ── Step 1: Store patient in database ────────────────────────
        self.db.add_patient(patient)

        # ── Step 2: Find matching doctors ────────────────────────────
        doctor, slot, search_notes = self._find_best_match(patient)

        if not doctor or not slot:
            return AgentResult(
                success=False,
                errors=[
                    f"No available doctor found for priority {patient.priority_tier} "
                    f"and specialization {patient.recommended_specialization}. "
                    "All matching slots are booked."
                ],
                warnings=search_notes,
            )

        # ── Step 3: Determine appointment date ──────────────────────
        appointment_date = self._determine_date(patient.priority_tier)

        # ── Step 4: Create the appointment ───────────────────────────
        appointment = Appointment(
            patient_id=patient.patient_id,
            patient_name=patient.name,
            doctor_id=doctor.doctor_id,
            doctor_name=doctor.name,
            specialization=doctor.specialization,
            time_slot=slot,
            priority_tier=patient.priority_tier,
            date=appointment_date,
        )

        try:
            self.db.create_appointment(appointment)
        except ValueError as e:
            return AgentResult(
                success=False,
                errors=[str(e)],
                warnings=warnings,
            )

        self.logger.info(
            "Appointment created: %s → Dr. %s @ %s on %s",
            appointment.appointment_id, doctor.name, slot, appointment_date,
        )

        # ── Step 5: Update context ───────────────────────────────────
        context["appointment"] = appointment
        context["assigned_doctor"] = doctor
        context["search_notes"] = search_notes

        return AgentResult(
            success=True,
            data=appointment,
            warnings=warnings + search_notes,
            metadata={
                "doctor_id": doctor.doctor_id,
                "doctor_name": doctor.name,
                "specialization": doctor.specialization,
                "time_slot": slot,
                "date": appointment_date,
                "appointment_id": appointment.appointment_id,
            },
        )

    # ─── Private Helper Methods ──────────────────────────────────────────

    def _find_best_match(
        self, patient: Patient
    ) -> tuple:
        """
        Multi-tier doctor search strategy:
        1. Exact match: specialization + priority
        2. Priority-only match (any specialization)
        3. Specialization-only match (any priority)
        4. Any available doctor

        Returns:
            Tuple of (Doctor, slot_string, search_notes_list)
        """
        search_notes = []
        priority = patient.priority_tier
        specialization = patient.recommended_specialization

        # ── Tier 1: Exact match ──────────────────────────────────────
        doctors = self.db.find_available_doctors(
            specialization=specialization,
            priority_tier=priority,
        )
        if doctors:
            doctor = doctors[0]
            slot = self._select_slot(doctor, priority)
            if slot:
                search_notes.append(
                    f"Exact match found: Dr. {doctor.name} ({doctor.specialization})"
                )
                return doctor, slot, search_notes

        search_notes.append(
            f"No exact match for {specialization} + {priority}."
        )

        # ── Tier 2: Priority-only match ──────────────────────────────
        doctors = self.db.find_available_doctors(priority_tier=priority)
        if doctors:
            doctor = doctors[0]
            slot = self._select_slot(doctor, priority)
            if slot:
                search_notes.append(
                    f"Priority match found: Dr. {doctor.name} ({doctor.specialization}). "
                    f"Ideal specialization was {specialization}."
                )
                return doctor, slot, search_notes

        search_notes.append(f"No priority-only match for {priority}.")

        # ── Tier 3: Specialization-only match ────────────────────────
        doctors = self.db.find_available_doctors(specialization=specialization)
        if doctors:
            doctor = doctors[0]
            slot = self._select_slot(doctor, priority)
            if slot:
                search_notes.append(
                    f"Specialization match found: Dr. {doctor.name}. "
                    f"Priority tier {priority} not in doctor's usual scope."
                )
                return doctor, slot, search_notes

        search_notes.append(f"No specialization match for {specialization}.")

        # ── Tier 4: Any available doctor ─────────────────────────────
        doctors = self.db.find_available_doctors()
        if doctors:
            doctor = doctors[0]
            slot = self._select_slot(doctor, priority)
            if slot:
                search_notes.append(
                    f"Fallback match: Dr. {doctor.name} ({doctor.specialization}). "
                    f"Not an ideal match but available."
                )
                return doctor, slot, search_notes

        search_notes.append("No available doctors found in the entire system.")
        return None, None, search_notes

    def _select_slot(self, doctor: Doctor, priority: str) -> Optional[str]:
        """
        Select the best available slot for the given priority.

        Strategy:
        - RED/ORANGE: First available (earliest) slot for urgency.
        - YELLOW/GREEN/BLUE: Mid-day slot preferred for convenience.
        """
        if not doctor.available_slots:
            return None

        slots = sorted(doctor.available_slots)

        if priority in ("RED", "ORANGE"):
            # Urgent: take the very next available slot
            return slots[0]
        else:
            # Non-urgent: prefer a mid-day slot
            mid_index = len(slots) // 2
            return slots[mid_index]

    def _determine_date(self, priority: str) -> str:
        """
        Determine the appointment date based on priority tier.

        - RED: Today (immediate)
        - ORANGE: Today
        - YELLOW: Today or tomorrow
        - GREEN: Within 2-3 days
        - BLUE: Within a week
        """
        today = datetime.now()

        day_offsets = {
            "RED": 0,
            "ORANGE": 0,
            "YELLOW": 0,
            "GREEN": 2,
            "BLUE": 5,
        }

        offset = day_offsets.get(priority, 1)
        target_date = today + timedelta(days=offset)

        return target_date.strftime("%Y-%m-%d")
