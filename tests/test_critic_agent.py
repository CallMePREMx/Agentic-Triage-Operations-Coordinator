"""
Tests for the Critic Agent.

Validates appointment confirmation, double-booking detection,
priority validation, and confirmation summary generation.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.critic_agent import CriticAgent
from data.mock_database import MockDatabase
from models.appointment import Appointment, AppointmentStatus
from models.patient import Patient


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database before each test."""
    db = MockDatabase()
    db.reset()
    yield


@pytest.fixture
def agent():
    return CriticAgent()


def make_appointment(**overrides):
    """Create a test appointment with defaults."""
    defaults = {
        "patient_id": "PAT-TEST01",
        "patient_name": "Test Patient",
        "doctor_id": "DOC-001",
        "doctor_name": "Sarah Chen",
        "specialization": "Emergency Medicine",
        "time_slot": "09:00",
        "priority_tier": "RED",
        "date": "2026-10-20",
    }
    defaults.update(overrides)
    return Appointment(**defaults)


def make_patient(**overrides):
    """Create a test patient with defaults."""
    defaults = {
        "name": "Test Patient",
        "age": 45,
        "symptoms": ["chest pain"],
        "symptom_duration": "2 hours",
    }
    defaults.update(overrides)
    p = Patient(**defaults)
    p.priority_tier = overrides.get("priority_tier", "RED")
    p.recommended_specialization = "Emergency Medicine"
    return p


class TestCriticValidation:
    """Tests for appointment validation."""

    def test_valid_appointment_confirmed(self, agent):
        """A valid appointment should be CONFIRMED."""
        appointment = make_appointment()
        patient = make_patient()
        context = {"patient": patient}

        # Store appointment in DB first
        db = MockDatabase()
        db.create_appointment(appointment)

        result = agent.run(appointment, context)
        assert result.success is True
        assert result.data.status == AppointmentStatus.CONFIRMED
        assert result.data.validated_by_critic is True

    def test_confirmation_summary_generated(self, agent):
        """Confirmed appointment should have a confirmation summary."""
        appointment = make_appointment()
        patient = make_patient()
        context = {"patient": patient}

        db = MockDatabase()
        db.create_appointment(appointment)

        result = agent.run(appointment, context)
        assert result.data.confirmation_summary is not None
        assert "APPOINTMENT CONFIRMATION" in result.data.confirmation_summary

    def test_invalid_input_type(self, agent):
        """Non-Appointment input should fail."""
        result = agent.run("not an appointment", {})
        assert result.success is False


class TestCriticCrossChecks:
    """Tests for cross-reference validation."""

    def test_priority_scope_warning(self, agent):
        """Doctor not handling the priority tier should produce a warning."""
        # DOC-011 (Dermatology) doesn't handle RED
        appointment = make_appointment(
            doctor_id="DOC-011",
            doctor_name="Lisa Nakamura",
            specialization="Dermatology",
            priority_tier="RED",
        )
        patient = make_patient(priority_tier="RED")
        context = {"patient": patient}

        db = MockDatabase()
        db.create_appointment(appointment)

        result = agent.run(appointment, context)
        # Should succeed but with warnings
        assert result.success is True
        assert len(result.warnings) > 0

    def test_context_updated(self, agent):
        """Context should be updated with validation results."""
        appointment = make_appointment()
        patient = make_patient()
        context = {"patient": patient}

        db = MockDatabase()
        db.create_appointment(appointment)

        agent.run(appointment, context)
        assert "validation_passed" in context
        assert "appointment" in context
