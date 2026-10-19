"""
Critic Agent (Validator Role).

Validates the final booking to ensure correctness: no double-bookings,
proper priority assignment, complete patient data. Generates a
confirmation summary and marks the appointment as CONFIRMED or flags issues.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.base_agent import AgentResult, BaseAgent
from data.mock_database import MockDatabase
from models.appointment import Appointment, AppointmentStatus
from models.patient import Patient
from utils.formatters import format_confirmation_summary
from utils.validators import (
    validate_appointment,
    validate_patient_data,
    validate_priority_assignment,
)


class CriticAgent(BaseAgent):
    """
    Critic Agent — the final agent in the pipeline.

    Responsibilities:
    1. Validate patient data completeness.
    2. Validate priority tier assignment is reasonable.
    3. Check for double-bookings and appointment conflicts.
    4. Confirm or reject the appointment.
    5. Generate a patient-facing confirmation summary.
    """

    def __init__(self):
        super().__init__(
            name="CriticAgent",
            role="Validator",
            description="Validates bookings, prevents conflicts, and generates confirmations.",
        )
        self.db = MockDatabase()

    def process(self, input_data: Any, context: Dict) -> AgentResult:
        """
        Validate the appointment and patient data end-to-end.

        Args:
            input_data: Appointment object from OperationsAgent.
            context: Shared pipeline context (must contain 'patient').

        Returns:
            AgentResult with validated Appointment (CONFIRMED or FAILED).
        """
        if not isinstance(input_data, Appointment):
            return AgentResult(
                success=False,
                errors=["CriticAgent expected an Appointment object."],
            )

        appointment = input_data
        patient = context.get("patient")
        all_issues: List[str] = []
        all_warnings: List[str] = []

        self.logger.info(
            "Validating appointment %s for patient %s.",
            appointment.appointment_id,
            appointment.patient_name,
        )

        # ── Step 1: Validate Patient Data ────────────────────────────
        if patient:
            patient_valid, patient_issues = validate_patient_data(patient)
            if not patient_valid:
                all_warnings.extend(patient_issues)
                self.logger.warning("Patient data issues: %s", patient_issues)

            # Validate priority assignment
            if patient.priority_tier:
                priority_valid, priority_concerns = validate_priority_assignment(
                    patient, patient.priority_tier
                )
                if not priority_valid:
                    all_warnings.extend(priority_concerns)
                    self.logger.warning("Priority concerns: %s", priority_concerns)
        else:
            all_warnings.append("Patient object not found in context; skipping patient validation.")

        # ── Step 2: Validate Appointment Integrity ───────────────────
        existing_appointments = self.db.get_all_appointments()
        appt_valid, appt_issues = validate_appointment(
            appointment, existing_appointments
        )

        if not appt_valid:
            # Check if any issues are critical (double-booking)
            critical_issues = [
                i for i in appt_issues
                if "double-booking" in i.lower() or "conflict" in i.lower()
            ]
            non_critical = [
                i for i in appt_issues
                if i not in critical_issues
            ]

            if critical_issues:
                all_issues.extend(critical_issues)
                self.logger.error("Critical validation failures: %s", critical_issues)
            all_warnings.extend(non_critical)

        # ── Step 3: Additional Cross-Checks ──────────────────────────
        cross_check_issues = self._cross_check(appointment, context)
        all_warnings.extend(cross_check_issues)

        # ── Step 4: Render Verdict ───────────────────────────────────
        if all_issues:
            # Critical issues found → FAIL the appointment
            appointment.status = AppointmentStatus.FAILED
            appointment.validated_by_critic = True
            appointment.validation_notes = all_issues + all_warnings

            self.logger.error(
                "Appointment %s FAILED validation: %s",
                appointment.appointment_id, all_issues,
            )

            context["appointment"] = appointment
            context["validation_passed"] = False

            return AgentResult(
                success=False,
                data=appointment,
                errors=all_issues,
                warnings=all_warnings,
                metadata={"validation_passed": False},
            )

        # No critical issues → CONFIRM the appointment
        appointment.confirm()
        appointment.validation_notes = all_warnings if all_warnings else ["All checks passed."]

        # Generate confirmation summary
        if patient:
            confirmation = format_confirmation_summary(patient, appointment)
            appointment.confirmation_summary = confirmation

        self.logger.info(
            "Appointment %s CONFIRMED. Warnings: %s",
            appointment.appointment_id,
            all_warnings if all_warnings else "None",
        )

        # ── Step 5: Update Context ───────────────────────────────────
        context["appointment"] = appointment
        context["validation_passed"] = True
        context["confirmation_summary"] = appointment.confirmation_summary

        return AgentResult(
            success=True,
            data=appointment,
            warnings=all_warnings,
            metadata={
                "validation_passed": True,
                "checks_performed": [
                    "patient_data_completeness",
                    "priority_assignment_review",
                    "double_booking_check",
                    "appointment_integrity",
                    "cross_reference_check",
                ],
                "warnings_count": len(all_warnings),
            },
        )

    def _cross_check(self, appointment: Appointment, context: Dict) -> List[str]:
        """
        Perform additional cross-reference validation.

        Returns list of warning messages.
        """
        warnings = []

        # Check if doctor exists in the database
        doctor = self.db.get_doctor(appointment.doctor_id)
        if not doctor:
            warnings.append(
                f"Doctor {appointment.doctor_id} not found in database."
            )
        else:
            # Check if the priority is within the doctor's scope
            if appointment.priority_tier not in doctor.handles_priority:
                warnings.append(
                    f"Dr. {doctor.name} does not typically handle "
                    f"{appointment.priority_tier} priority cases. "
                    f"Handles: {', '.join(doctor.handles_priority)}"
                )

            # Verify specialization matches
            if appointment.specialization != doctor.specialization:
                warnings.append(
                    f"Appointment specialization ({appointment.specialization}) "
                    f"doesn't match doctor's specialization ({doctor.specialization})."
                )

        # Check patient doesn't have too many same-day appointments
        patient_appointments = self.db.get_appointments_by_patient(
            appointment.patient_id
        )
        same_day = [
            a for a in patient_appointments
            if a.date == appointment.date
            and a.appointment_id != appointment.appointment_id
        ]
        if same_day:
            warnings.append(
                f"Patient already has {len(same_day)} other appointment(s) on {appointment.date}."
            )

        return warnings
