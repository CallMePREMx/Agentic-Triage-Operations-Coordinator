"""
Tests for the Mock Database.

Validates CRUD operations, doctor matching, double-booking prevention,
slot management, and CSV export.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.mock_database import MockDatabase
from models.appointment import Appointment, AppointmentStatus
from models.patient import Patient


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the singleton database before each test."""
    db = MockDatabase()
    db.reset()
    yield


@pytest.fixture
def db():
    return MockDatabase()


class TestDoctorOperations:
    """Tests for doctor-related database operations."""

    def test_seed_doctors_loaded(self, db):
        """Database should be seeded with 12 doctors."""
        doctors = db.get_all_doctors()
        assert len(doctors) == 12

    def test_find_emergency_doctors(self, db):
        """Should find doctors who handle RED priority."""
        doctors = db.find_available_doctors(priority_tier="RED")
        assert len(doctors) > 0
        for doc in doctors:
            assert "RED" in doc.handles_priority

    def test_find_by_specialization(self, db):
        """Should find doctors by specialization."""
        doctors = db.find_available_doctors(specialization="Cardiology")
        assert len(doctors) >= 1
        for doc in doctors:
            assert doc.specialization == "Cardiology"

    def test_find_combined_filter(self, db):
        """Should filter by both specialization and priority."""
        doctors = db.find_available_doctors(
            specialization="Emergency Medicine", priority_tier="RED"
        )
        assert len(doctors) >= 1
        for doc in doctors:
            assert doc.specialization == "Emergency Medicine"
            assert "RED" in doc.handles_priority

    def test_get_doctor_by_id(self, db):
        """Should retrieve a doctor by ID."""
        doc = db.get_doctor("DOC-001")
        assert doc is not None
        assert doc.name == "Sarah Chen"


class TestAppointmentOperations:
    """Tests for appointment CRUD operations."""

    def test_create_appointment(self, db):
        """Should create and store an appointment."""
        appt = Appointment(
            patient_id="PAT-001",
            patient_name="Test",
            doctor_id="DOC-001",
            doctor_name="Sarah Chen",
            specialization="Emergency Medicine",
            time_slot="09:00",
            priority_tier="RED",
            date="2026-10-20",
        )
        created = db.create_appointment(appt)
        assert created.appointment_id == appt.appointment_id
        assert db.get_appointment(appt.appointment_id) is not None

    def test_slot_removed_after_booking(self, db):
        """Booking should remove the slot from the doctor's availability."""
        doc = db.get_doctor("DOC-001")
        assert "09:00" in doc.available_slots

        appt = Appointment(
            patient_id="PAT-001",
            patient_name="Test",
            doctor_id="DOC-001",
            doctor_name="Sarah Chen",
            specialization="Emergency Medicine",
            time_slot="09:00",
            priority_tier="RED",
            date="2026-10-20",
        )
        db.create_appointment(appt)

        doc = db.get_doctor("DOC-001")
        assert "09:00" not in doc.available_slots

    def test_double_booking_prevented(self, db):
        """Should raise ValueError for double-booking."""
        appt1 = Appointment(
            patient_id="PAT-001", patient_name="P1",
            doctor_id="DOC-001", doctor_name="Sarah Chen",
            specialization="Emergency Medicine",
            time_slot="10:00", priority_tier="RED", date="2026-10-20",
        )
        appt2 = Appointment(
            patient_id="PAT-002", patient_name="P2",
            doctor_id="DOC-001", doctor_name="Sarah Chen",
            specialization="Emergency Medicine",
            time_slot="10:00", priority_tier="RED", date="2026-10-20",
        )
        db.create_appointment(appt1)
        with pytest.raises(ValueError, match="Double-booking"):
            db.create_appointment(appt2)

    def test_cancel_appointment(self, db):
        """Should cancel an appointment and release the slot."""
        appt = Appointment(
            patient_id="PAT-001", patient_name="Test",
            doctor_id="DOC-001", doctor_name="Sarah Chen",
            specialization="Emergency Medicine",
            time_slot="11:00", priority_tier="RED", date="2026-10-20",
        )
        db.create_appointment(appt)
        assert "11:00" not in db.get_doctor("DOC-001").available_slots

        result = db.cancel_appointment(appt.appointment_id, "Testing")
        assert result is True
        assert "11:00" in db.get_doctor("DOC-001").available_slots


class TestPatientOperations:
    """Tests for patient operations."""

    def test_add_and_get_patient(self, db):
        """Should store and retrieve a patient."""
        patient = Patient(
            name="Test Patient", age=30,
            symptoms=["headache"], symptom_duration="1 day",
        )
        db.add_patient(patient)
        retrieved = db.get_patient(patient.patient_id)
        assert retrieved is not None
        assert retrieved.name == "Test Patient"


class TestStatistics:
    """Tests for database statistics."""

    def test_initial_stats(self, db):
        """Fresh database should have correct initial stats."""
        stats = db.get_statistics()
        assert stats["total_doctors"] == 12
        assert stats["total_patients"] == 0
        assert stats["total_appointments"] == 0
