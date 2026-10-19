"""
Validation utilities used by the Critic Agent and other components.

Provides functions to validate patient data completeness, appointment
integrity, and business rules.
"""

from __future__ import annotations

from typing import List, Tuple

from models.patient import Patient
from models.appointment import Appointment, AppointmentStatus
from config.settings import PRIORITY_TIERS


def validate_patient_data(patient: Patient) -> Tuple[bool, List[str]]:
    """
    Validate that a patient record has all required fields.

    Args:
        patient: Patient instance to validate.

    Returns:
        Tuple of (is_valid, list_of_issues).
    """
    issues = []

    if not patient.name or patient.name.strip() == "":
        issues.append("Patient name is missing.")
    if patient.age is None or patient.age < 0 or patient.age > 150:
        issues.append(f"Invalid patient age: {patient.age}")
    if not patient.symptoms:
        issues.append("No symptoms recorded for the patient.")
    if not patient.symptom_duration:
        issues.append("Symptom duration is missing.")
    if patient.priority_tier and patient.priority_tier not in PRIORITY_TIERS:
        issues.append(f"Invalid priority tier: {patient.priority_tier}")

    return (len(issues) == 0, issues)


def validate_appointment(
    appointment: Appointment,
    existing_appointments: List[Appointment],
) -> Tuple[bool, List[str]]:
    """
    Validate an appointment for correctness and conflicts.

    Checks:
    - Required fields are present
    - No double-booking with existing appointments
    - Priority tier is valid
    - Time slot format is correct

    Args:
        appointment: The appointment to validate.
        existing_appointments: List of existing appointments to check against.

    Returns:
        Tuple of (is_valid, list_of_issues).
    """
    issues = []

    # ── Required Fields ──────────────────────────────────────────────
    if not appointment.patient_id:
        issues.append("Patient ID is missing.")
    if not appointment.doctor_id:
        issues.append("Doctor ID is missing.")
    if not appointment.time_slot:
        issues.append("Time slot is missing.")
    if not appointment.date:
        issues.append("Appointment date is missing.")

    # ── Priority Tier ────────────────────────────────────────────────
    if appointment.priority_tier not in PRIORITY_TIERS:
        issues.append(f"Invalid priority tier: {appointment.priority_tier}")

    # ── Time Slot Format (HH:MM) ────────────────────────────────────
    import re
    if appointment.time_slot and not re.match(r"^\d{2}:\d{2}$", appointment.time_slot):
        issues.append(f"Invalid time slot format: {appointment.time_slot}")

    # ── Double-Booking Check ─────────────────────────────────────────
    for existing in existing_appointments:
        if (
            existing.appointment_id != appointment.appointment_id
            and existing.doctor_id == appointment.doctor_id
            and existing.time_slot == appointment.time_slot
            and existing.date == appointment.date
            and existing.status not in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.FAILED,
            )
        ):
            issues.append(
                f"Double-booking conflict: Dr. {appointment.doctor_name} "
                f"already has appointment {existing.appointment_id} "
                f"at {appointment.time_slot} on {appointment.date}."
            )
            break

    # ── Patient Double-Booking Check ─────────────────────────────────
    for existing in existing_appointments:
        if (
            existing.appointment_id != appointment.appointment_id
            and existing.patient_id == appointment.patient_id
            and existing.time_slot == appointment.time_slot
            and existing.date == appointment.date
            and existing.status not in (
                AppointmentStatus.CANCELLED,
                AppointmentStatus.FAILED,
            )
        ):
            issues.append(
                f"Patient {appointment.patient_name} already has "
                f"appointment {existing.appointment_id} at the same time."
            )
            break

    return (len(issues) == 0, issues)


def validate_priority_assignment(
    patient: Patient,
    assigned_tier: str,
) -> Tuple[bool, List[str]]:
    """
    Validate that a priority assignment is reasonable for the patient's data.

    Args:
        patient: The patient with symptoms.
        assigned_tier: The priority tier assigned by the Triage Agent.

    Returns:
        Tuple of (is_reasonable, list_of_concerns).
    """
    concerns = []

    if assigned_tier not in PRIORITY_TIERS:
        concerns.append(f"Unknown priority tier: {assigned_tier}")
        return (False, concerns)

    tier_level = PRIORITY_TIERS[assigned_tier]["level"]

    # Age-based sanity checks
    if patient.age is not None:
        if patient.age < 2 and tier_level > 3:
            concerns.append(
                f"Infant (age {patient.age}) assigned low priority "
                f"({assigned_tier}). Review recommended."
            )
        if patient.age > 75 and tier_level > 3:
            concerns.append(
                f"Elderly patient (age {patient.age}) assigned low priority "
                f"({assigned_tier}). Review recommended."
            )

    # Symptom count sanity check
    if len(patient.symptoms) >= 4 and tier_level > 3:
        concerns.append(
            f"Patient has {len(patient.symptoms)} symptoms but assigned "
            f"low priority ({assigned_tier}). Review recommended."
        )

    return (len(concerns) == 0, concerns)
