"""
Output formatting utilities.

Provides functions to format agent outputs, confirmation summaries,
and audit trail reports for both CLI and web display.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from config.settings import PRIORITY_TIERS
from models.appointment import Appointment
from models.patient import Patient


def format_confirmation_summary(
    patient: Patient,
    appointment: Appointment,
) -> str:
    """
    Generate a formatted confirmation summary for a booked appointment.

    Args:
        patient: The patient record.
        appointment: The confirmed appointment.

    Returns:
        Multi-line confirmation summary string.
    """
    tier_info = PRIORITY_TIERS.get(appointment.priority_tier, {})
    tier_label = tier_info.get("label", appointment.priority_tier)
    max_wait = tier_info.get("max_wait_minutes", "N/A")

    summary = f"""
╔══════════════════════════════════════════════════════════════╗
║              APPOINTMENT CONFIRMATION                       ║
╠══════════════════════════════════════════════════════════════╣
║  Confirmation ID : {appointment.appointment_id:<40s}║
║  Status          : {appointment.status.value:<40s}║
╠══════════════════════════════════════════════════════════════╣
║  PATIENT DETAILS                                            ║
║  Name            : {patient.name:<40s}║
║  Patient ID      : {patient.patient_id:<40s}║
║  Age             : {str(patient.age):<40s}║
║  Symptoms        : {', '.join(patient.symptoms)[:40]:<40s}║
╠══════════════════════════════════════════════════════════════╣
║  APPOINTMENT DETAILS                                        ║
║  Doctor           : Dr. {appointment.doctor_name:<35s}║
║  Specialization   : {appointment.specialization:<39s}║
║  Date             : {appointment.date:<39s}║
║  Time Slot        : {appointment.time_slot:<39s}║
║  Priority         : {f'{appointment.priority_tier} ({tier_label})':<39s}║
║  Max Wait Time    : {f'{max_wait} minutes':<39s}║
╠══════════════════════════════════════════════════════════════╣
║  Validated by Critic Agent: {'Yes' if appointment.validated_by_critic else 'No':<31s}║
╚══════════════════════════════════════════════════════════════╝
""".strip()

    return summary


def format_triage_report(patient: Patient) -> str:
    """
    Format a triage assessment report.

    Args:
        patient: The triaged patient with priority and severity data.

    Returns:
        Formatted triage report string.
    """
    tier = patient.priority_tier or "UNASSESSED"
    tier_info = PRIORITY_TIERS.get(tier, {})
    tier_label = tier_info.get("label", "Unknown")
    tier_desc = tier_info.get("description", "")
    score = patient.severity_score or 0.0

    severity_bar = _create_severity_bar(score)

    report = f"""
┌─────────────────────────────────────────────────────┐
│              TRIAGE ASSESSMENT REPORT                │
├─────────────────────────────────────────────────────┤
│  Patient       : {patient.name:<35s}│
│  Age           : {str(patient.age):<35s}│
│  Symptoms      : {', '.join(patient.symptoms)[:35]:<35s}│
│  Duration      : {patient.symptom_duration:<35s}│
├─────────────────────────────────────────────────────┤
│  TRIAGE RESULT                                      │
│  Priority Tier : {f'{tier} ({tier_label})':<35s}│
│  Severity      : {severity_bar:<35s}│
│  Score         : {f'{score:.2f} / 1.00':<35s}│
│  Specialization: {(patient.recommended_specialization or 'General'):<35s}│
├─────────────────────────────────────────────────────┤
│  {tier_desc[:51]:<51s}│
├─────────────────────────────────────────────────────┤
│  NOTES                                              │
""".strip()

    for note in patient.triage_notes:
        report += f"\n│  • {note[:49]:<49s}│"

    report += "\n└─────────────────────────────────────────────────────┘"
    return report


def format_agent_step(
    agent_name: str,
    action: str,
    details: str,
    step_number: int,
) -> str:
    """
    Format a single agent processing step for the audit trail.

    Args:
        agent_name: Name of the agent performing the action.
        action: Brief description of the action taken.
        details: Detailed description of the result.
        step_number: Sequential step number.

    Returns:
        Formatted step string.
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    return (
        f"[Step {step_number}] [{timestamp}] {agent_name}\n"
        f"  Action  : {action}\n"
        f"  Details : {details}"
    )


def format_pipeline_summary(steps: List[Dict]) -> str:
    """
    Format the complete pipeline execution summary.

    Args:
        steps: List of step dictionaries from the orchestrator.

    Returns:
        Formatted pipeline summary string.
    """
    lines = [
        "═" * 60,
        "  PIPELINE EXECUTION SUMMARY",
        "═" * 60,
    ]

    for step in steps:
        status_icon = "✓" if step.get("success", True) else "✗"
        lines.append(
            f"  {status_icon} Step {step['step']}: {step['agent']} — {step['action']}"
        )
        if step.get("details"):
            lines.append(f"    └─ {step['details']}")

    lines.append("═" * 60)
    return "\n".join(lines)


def _create_severity_bar(score: float, width: int = 20) -> str:
    """Create a visual severity bar: [████████░░░░░░░░░░░░] 0.65"""
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score:.2f}"


def format_doctor_availability(doctors: list) -> str:
    """
    Format a list of available doctors for display.

    Args:
        doctors: List of Doctor objects.

    Returns:
        Formatted availability table string.
    """
    if not doctors:
        return "No doctors available matching the criteria."

    lines = [
        "┌────────────┬──────────────────────┬──────────────────────┬────────────┐",
        "│ Doctor ID  │ Name                 │ Specialization       │ Slots Left │",
        "├────────────┼──────────────────────┼──────────────────────┼────────────┤",
    ]

    for doc in doctors:
        lines.append(
            f"│ {doc.doctor_id:<10s} │ {doc.name:<20s} │ "
            f"{doc.specialization:<20s} │ {len(doc.available_slots):>10d} │"
        )

    lines.append(
        "└────────────┴──────────────────────┴──────────────────────┴────────────┘"
    )
    return "\n".join(lines)
