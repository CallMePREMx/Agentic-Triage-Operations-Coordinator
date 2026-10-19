"""
Mock database for the triage system.

Provides an in-memory store backed by CSV persistence for doctors,
appointments, and patients. Acts as the single source of truth for
all data operations in the system.
"""

from __future__ import annotations

import csv
import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import (
    CSV_DIR,
    SLOT_DURATION_MINUTES,
    WORKING_HOURS_END,
    WORKING_HOURS_START,
)
from config.logging_config import get_agent_logger
from models.appointment import Appointment, AppointmentStatus
from models.doctor import Doctor
from models.patient import Patient

logger = get_agent_logger("MockDatabase")


class MockDatabase:
    """
    Thread-safe mock database with CSV persistence.

    Stores doctors, patients, and appointments in-memory with
    optional CSV file backing for data persistence across runs.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> MockDatabase:
        """Singleton pattern to ensure one database instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._data_lock = threading.Lock()

        # In-memory stores
        self.doctors: Dict[str, Doctor] = {}
        self.patients: Dict[str, Patient] = {}
        self.appointments: Dict[str, Appointment] = {}

        # Initialize with seed data
        self._seed_doctors()
        logger.info(
            "Database initialized with %d doctors", len(self.doctors)
        )

    def reset(self) -> None:
        """Reset the database to initial state (useful for testing)."""
        with self._data_lock:
            self.doctors.clear()
            self.patients.clear()
            self.appointments.clear()
            self._seed_doctors()
            logger.info("Database reset to initial state.")

    # ─── Seed Data ────────────────────────────────────────────────────────

    def _generate_time_slots(self) -> List[str]:
        """Generate 30-minute time slots for a working day."""
        slots = []
        current = WORKING_HOURS_START * 60  # Convert to minutes
        end = WORKING_HOURS_END * 60
        while current < end:
            hours, mins = divmod(current, 60)
            slots.append(f"{hours:02d}:{mins:02d}")
            current += SLOT_DURATION_MINUTES
        return slots

    def _seed_doctors(self) -> None:
        """Populate the database with a realistic set of mock doctors."""
        all_slots = self._generate_time_slots()

        seed_data = [
            {
                "doctor_id": "DOC-001",
                "name": "Sarah Chen",
                "specialization": "Emergency Medicine",
                "handles_priority": ["RED", "ORANGE"],
                "max_patients_per_day": 25,
                "slots": all_slots[:],
            },
            {
                "doctor_id": "DOC-002",
                "name": "James Rodriguez",
                "specialization": "Emergency Medicine",
                "handles_priority": ["RED", "ORANGE", "YELLOW"],
                "max_patients_per_day": 25,
                "slots": all_slots[:],
            },
            {
                "doctor_id": "DOC-003",
                "name": "Priya Sharma",
                "specialization": "Cardiology",
                "handles_priority": ["RED", "ORANGE", "YELLOW"],
                "max_patients_per_day": 18,
                "slots": all_slots[2:],  # Starts at 09:00
            },
            {
                "doctor_id": "DOC-004",
                "name": "Michael Foster",
                "specialization": "Neurology",
                "handles_priority": ["RED", "ORANGE", "YELLOW"],
                "max_patients_per_day": 16,
                "slots": all_slots[2:20],  # 09:00 – 18:00
            },
            {
                "doctor_id": "DOC-005",
                "name": "Aisha Khan",
                "specialization": "General Medicine",
                "handles_priority": ["YELLOW", "GREEN", "BLUE"],
                "max_patients_per_day": 30,
                "slots": all_slots[:],
            },
            {
                "doctor_id": "DOC-006",
                "name": "David Park",
                "specialization": "General Medicine",
                "handles_priority": ["ORANGE", "YELLOW", "GREEN", "BLUE"],
                "max_patients_per_day": 28,
                "slots": all_slots[:],
            },
            {
                "doctor_id": "DOC-007",
                "name": "Elena Volkov",
                "specialization": "Orthopedics",
                "handles_priority": ["ORANGE", "YELLOW", "GREEN"],
                "max_patients_per_day": 20,
                "slots": all_slots[2:20],
            },
            {
                "doctor_id": "DOC-008",
                "name": "Robert Kim",
                "specialization": "Pediatrics",
                "handles_priority": ["RED", "ORANGE", "YELLOW", "GREEN", "BLUE"],
                "max_patients_per_day": 25,
                "slots": all_slots[2:],
            },
            {
                "doctor_id": "DOC-009",
                "name": "Fatima Al-Hassan",
                "specialization": "Pulmonology",
                "handles_priority": ["RED", "ORANGE", "YELLOW"],
                "max_patients_per_day": 18,
                "slots": all_slots[4:20],  # 10:00 – 18:00
            },
            {
                "doctor_id": "DOC-010",
                "name": "Thomas Wright",
                "specialization": "Gastroenterology",
                "handles_priority": ["ORANGE", "YELLOW", "GREEN"],
                "max_patients_per_day": 18,
                "slots": all_slots[2:20],
            },
            {
                "doctor_id": "DOC-011",
                "name": "Lisa Nakamura",
                "specialization": "Dermatology",
                "handles_priority": ["YELLOW", "GREEN", "BLUE"],
                "max_patients_per_day": 22,
                "slots": all_slots[4:18],  # 10:00 – 17:00
            },
            {
                "doctor_id": "DOC-012",
                "name": "Ahmed Patel",
                "specialization": "ENT",
                "handles_priority": ["YELLOW", "GREEN", "BLUE"],
                "max_patients_per_day": 20,
                "slots": all_slots[2:18],  # 09:00 – 17:00
            },
        ]

        for doc_data in seed_data:
            doctor = Doctor(
                doctor_id=doc_data["doctor_id"],
                name=doc_data["name"],
                specialization=doc_data["specialization"],
                available_slots=doc_data["slots"],
                handles_priority=doc_data["handles_priority"],
                max_patients_per_day=doc_data["max_patients_per_day"],
            )
            self.doctors[doctor.doctor_id] = doctor

    # ─── Patient Operations ──────────────────────────────────────────────

    def add_patient(self, patient: Patient) -> Patient:
        """Store a patient record."""
        with self._data_lock:
            self.patients[patient.patient_id] = patient
            logger.info("Patient added: %s", patient.patient_id)
            return patient

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        """Retrieve a patient by ID."""
        return self.patients.get(patient_id)

    def get_all_patients(self) -> List[Patient]:
        """Retrieve all patients."""
        return list(self.patients.values())

    # ─── Doctor Operations ───────────────────────────────────────────────

    def get_doctor(self, doctor_id: str) -> Optional[Doctor]:
        """Retrieve a doctor by ID."""
        return self.doctors.get(doctor_id)

    def get_all_doctors(self) -> List[Doctor]:
        """Retrieve all doctors."""
        return list(self.doctors.values())

    def find_available_doctors(
        self,
        specialization: Optional[str] = None,
        priority_tier: Optional[str] = None,
    ) -> List[Doctor]:
        """
        Find doctors matching specialization and priority tier with open slots.

        Args:
            specialization: Filter by doctor's specialization.
            priority_tier: Filter by doctors who handle this priority level.

        Returns:
            List of matching available doctors, sorted by slot availability.
        """
        with self._data_lock:
            results = []
            for doctor in self.doctors.values():
                if not doctor.is_available:
                    continue
                if specialization and doctor.specialization != specialization:
                    continue
                if priority_tier and priority_tier not in doctor.handles_priority:
                    continue
                results.append(doctor)

            # Sort: prefer doctors with more available slots
            results.sort(key=lambda d: len(d.available_slots), reverse=True)
            return results

    # ─── Appointment Operations ──────────────────────────────────────────

    def create_appointment(self, appointment: Appointment) -> Appointment:
        """
        Store an appointment and book the doctor's slot.

        Args:
            appointment: The appointment to create.

        Returns:
            The stored appointment.

        Raises:
            ValueError: If the slot is already booked (double-booking).
        """
        with self._data_lock:
            # Check for double-booking
            if self._is_double_booked(
                appointment.doctor_id, appointment.time_slot, appointment.date
            ):
                raise ValueError(
                    f"Double-booking detected: Dr. {appointment.doctor_name} "
                    f"already has a patient at {appointment.time_slot} on {appointment.date}"
                )

            # Book the doctor's slot
            doctor = self.doctors.get(appointment.doctor_id)
            if doctor:
                doctor.book_slot(appointment.time_slot)

            self.appointments[appointment.appointment_id] = appointment
            logger.info(
                "Appointment created: %s (Patient: %s → Dr. %s @ %s)",
                appointment.appointment_id,
                appointment.patient_name,
                appointment.doctor_name,
                appointment.time_slot,
            )
            return appointment

    def cancel_appointment(self, appointment_id: str, reason: str = "") -> bool:
        """Cancel an appointment and release the doctor's slot."""
        with self._data_lock:
            appt = self.appointments.get(appointment_id)
            if not appt:
                return False

            appt.cancel(reason)

            # Release the doctor's slot
            doctor = self.doctors.get(appt.doctor_id)
            if doctor:
                doctor.release_slot(appt.time_slot)

            logger.info("Appointment cancelled: %s", appointment_id)
            return True

    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        """Retrieve an appointment by ID."""
        return self.appointments.get(appointment_id)

    def get_all_appointments(self) -> List[Appointment]:
        """Retrieve all appointments."""
        return list(self.appointments.values())

    def get_appointments_by_doctor(
        self, doctor_id: str, date: Optional[str] = None
    ) -> List[Appointment]:
        """Get all appointments for a specific doctor, optionally filtered by date."""
        results = []
        for appt in self.appointments.values():
            if appt.doctor_id != doctor_id:
                continue
            if appt.status == AppointmentStatus.CANCELLED:
                continue
            if date and appt.date != date:
                continue
            results.append(appt)
        results.sort(key=lambda a: a.time_slot)
        return results

    def get_appointments_by_patient(self, patient_id: str) -> List[Appointment]:
        """Get all appointments for a specific patient."""
        return [
            appt
            for appt in self.appointments.values()
            if appt.patient_id == patient_id
            and appt.status != AppointmentStatus.CANCELLED
        ]

    # ─── Validation Helpers ──────────────────────────────────────────────

    def _is_double_booked(
        self, doctor_id: str, time_slot: str, date: str
    ) -> bool:
        """Check if a doctor already has a booking at the given slot and date."""
        for appt in self.appointments.values():
            if (
                appt.doctor_id == doctor_id
                and appt.time_slot == time_slot
                and appt.date == date
                and appt.status not in (AppointmentStatus.CANCELLED, AppointmentStatus.FAILED)
            ):
                return True
        return False

    def check_double_booking(
        self, doctor_id: str, time_slot: str, date: str
    ) -> Optional[Appointment]:
        """
        Check for double-booking and return the conflicting appointment if found.

        Returns:
            The conflicting Appointment, or None if no conflict.
        """
        with self._data_lock:
            for appt in self.appointments.values():
                if (
                    appt.doctor_id == doctor_id
                    and appt.time_slot == time_slot
                    and appt.date == date
                    and appt.status not in (
                        AppointmentStatus.CANCELLED,
                        AppointmentStatus.FAILED,
                    )
                ):
                    return appt
            return None

    # ─── CSV Persistence ─────────────────────────────────────────────────

    def export_appointments_csv(self, filepath: Optional[Path] = None) -> Path:
        """Export all appointments to CSV."""
        filepath = filepath or CSV_DIR / "appointments.csv"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "appointment_id", "patient_id", "patient_name",
            "doctor_id", "doctor_name", "specialization",
            "time_slot", "priority_tier", "date", "status",
            "validated_by_critic", "created_at",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for appt in self.appointments.values():
                row = appt.to_dict()
                row["status"] = appt.status.value
                writer.writerow({k: row.get(k, "") for k in fieldnames})

        logger.info("Appointments exported to %s", filepath)
        return filepath

    def export_doctors_csv(self, filepath: Optional[Path] = None) -> Path:
        """Export all doctors to CSV."""
        filepath = filepath or CSV_DIR / "doctors.csv"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "doctor_id", "name", "specialization",
            "handles_priority", "available_slots_count",
            "max_patients_per_day", "current_patient_count",
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for doc in self.doctors.values():
                writer.writerow({
                    "doctor_id": doc.doctor_id,
                    "name": doc.name,
                    "specialization": doc.specialization,
                    "handles_priority": json.dumps(doc.handles_priority),
                    "available_slots_count": len(doc.available_slots),
                    "max_patients_per_day": doc.max_patients_per_day,
                    "current_patient_count": doc.current_patient_count,
                })

        logger.info("Doctors exported to %s", filepath)
        return filepath

    # ─── Statistics ──────────────────────────────────────────────────────

    def get_statistics(self) -> dict:
        """Get a summary of database statistics."""
        active_appointments = [
            a for a in self.appointments.values()
            if a.status not in (AppointmentStatus.CANCELLED, AppointmentStatus.FAILED)
        ]
        priority_counts = {}
        spec_counts = {}
        for appt in active_appointments:
            tier = appt.priority_tier
            priority_counts[tier] = priority_counts.get(tier, 0) + 1
            spec = appt.specialization
            spec_counts[spec] = spec_counts.get(spec, 0) + 1

        total_slots = sum(len(d.available_slots) for d in self.doctors.values())
        total_capacity = sum(d.max_patients_per_day for d in self.doctors.values())
        utilization = (
            f"{(len(active_appointments) / total_capacity * 100):.1f}%"
            if total_capacity > 0
            else "0.0%"
        )

        return {
            "total_doctors": len(self.doctors),
            "total_patients": len(self.patients),
            "total_appointments": len(self.appointments),
            "active_appointments": len(active_appointments),
            "priority_distribution": priority_counts,
            "appointments_by_priority": priority_counts,
            "appointments_by_specialization": spec_counts,
            "available_slots": total_slots,
            "total_daily_capacity": total_capacity,
            "utilization_rate": utilization,
        }
