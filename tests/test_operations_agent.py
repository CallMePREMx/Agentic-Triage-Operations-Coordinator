"""
Tests for the Operations Agent.

Validates doctor matching, slot selection, appointment creation,
and fallback strategies.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.operations_agent import OperationsAgent
from data.mock_database import MockDatabase
from models.patient import Patient


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database before each test."""
    db = MockDatabase()
    db.reset()
    yield


@pytest.fixture
def agent():
    return OperationsAgent()


def make_triaged_patient(priority, specialization, name="Test Patient", age=30):
    """Create a patient that has already been triaged."""
    p = Patient(name=name, age=age, symptoms=["test"], symptom_duration="1 day")
    p.priority_tier = priority
    p.recommended_specialization = specialization
    return p


class TestDoctorMatching:
    """Tests for doctor matching strategies."""

    def test_exact_match(self, agent):
        """Test finding a doctor matching both specialization and priority."""
        patient = make_triaged_patient("RED", "Emergency Medicine")
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.specialization == "Emergency Medicine"

    def test_priority_fallback(self, agent):
        """Test fallback when exact specialization isn't available."""
        patient = make_triaged_patient("RED", "Nonexistent Specialty")
        result = agent.run(patient, {})
        assert result.success is True
        # Should find a doctor who handles RED priority
        assert result.data.priority_tier == "RED"

    def test_routine_appointment(self, agent):
        """Test scheduling a routine GREEN appointment."""
        patient = make_triaged_patient("GREEN", "General Medicine")
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.priority_tier == "GREEN"

    def test_appointment_creation_in_db(self, agent):
        """Test that the appointment is stored in the database."""
        patient = make_triaged_patient("YELLOW", "General Medicine")
        context = {}
        result = agent.run(patient, context)
        assert result.success is True

        db = MockDatabase()
        appt = db.get_appointment(result.data.appointment_id)
        assert appt is not None
        assert appt.patient_name == "Test Patient"


class TestSlotSelection:
    """Tests for slot selection strategy."""

    def test_emergency_gets_earliest_slot(self, agent):
        """RED priority should get the earliest available slot."""
        patient = make_triaged_patient("RED", "Emergency Medicine")
        result = agent.run(patient, {})
        assert result.success is True
        # Slot should be early in the day
        hour = int(result.data.time_slot.split(":")[0])
        assert hour <= 10  # Should be an early slot

    def test_patient_stored_in_db(self, agent):
        """Patient should be stored in the database."""
        patient = make_triaged_patient("GREEN", "General Medicine")
        agent.run(patient, {})
        db = MockDatabase()
        stored = db.get_patient(patient.patient_id)
        assert stored is not None


class TestOperationsEdgeCases:
    """Edge case tests."""

    def test_no_triage_fails(self, agent):
        """Patient without priority tier should fail."""
        patient = Patient(name="No Triage", age=30, symptoms=["test"], symptom_duration="1 day")
        result = agent.run(patient, {})
        assert result.success is False

    def test_invalid_input(self, agent):
        """Non-Patient input should fail."""
        result = agent.run("invalid", {})
        assert result.success is False
