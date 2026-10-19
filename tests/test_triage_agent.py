"""
Tests for the Triage Agent.

Validates severity scoring, priority tier assignment, red-flag detection,
age/duration modifiers, and specialization recommendation.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.triage_agent import TriageAgent
from models.patient import Patient


@pytest.fixture
def agent():
    return TriageAgent()


def make_patient(symptoms, age=30, duration="1 day"):
    """Helper to create a patient with given symptoms."""
    return Patient(
        name="Test Patient",
        age=age,
        symptoms=symptoms,
        symptom_duration=duration,
    )


class TestTriagePriority:
    """Tests for priority tier assignment."""

    def test_emergency_chest_pain_sob(self, agent):
        """Chest pain + shortness of breath should trigger RED (red-flag combo)."""
        patient = make_patient(["chest pain", "shortness of breath"], age=55)
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.priority_tier == "RED"

    def test_routine_cough(self, agent):
        """Simple cough should be GREEN or BLUE."""
        patient = make_patient(["cough"], age=25, duration="5 days")
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.priority_tier in ("GREEN", "BLUE")

    def test_urgent_severe_headache(self, agent):
        """Severe headache should be at least ORANGE."""
        patient = make_patient(["severe headache"], age=40, duration="6 hours")
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.priority_tier in ("RED", "ORANGE")

    def test_seizure_red(self, agent):
        """Seizure should be RED."""
        patient = make_patient(["seizure"], age=20)
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.priority_tier == "RED"


class TestTriageModifiers:
    """Tests for severity modifiers."""

    def test_elderly_modifier(self, agent):
        """Elderly patients should get higher severity."""
        young = make_patient(["fever"], age=25)
        old = make_patient(["fever"], age=80)
        r_young = agent.run(young, {})
        r_old = agent.run(old, {})
        assert r_old.data.severity_score > r_young.data.severity_score

    def test_infant_modifier(self, agent):
        """Infants should get higher severity than adults."""
        adult = make_patient(["fever"], age=30)
        infant = make_patient(["fever"], age=0)
        r_adult = agent.run(adult, {})
        r_infant = agent.run(infant, {})
        assert r_infant.data.severity_score > r_adult.data.severity_score

    def test_acute_onset_modifier(self, agent):
        """Acute onset (minutes) should score higher than chronic (months)."""
        acute = make_patient(["headache"], age=30, duration="30 minutes")
        chronic = make_patient(["headache"], age=30, duration="3 months")
        r_acute = agent.run(acute, {})
        r_chronic = agent.run(chronic, {})
        assert r_acute.data.severity_score > r_chronic.data.severity_score


class TestTriageRedFlags:
    """Tests for red-flag combination detection."""

    def test_meningitis_red_flag(self, agent):
        """Severe headache + stiff neck + fever should trigger red flag."""
        patient = make_patient(
            ["severe headache", "fever"], age=25, duration="2 hours"
        )
        result = agent.run(patient, {})
        assert result.success is True
        # Should be elevated due to escalation factors
        assert result.data.priority_tier in ("RED", "ORANGE")

    def test_no_symptoms_fallback(self, agent):
        """Unknown symptoms should fall back to GREEN."""
        patient = make_patient(["general discomfort"], age=30)
        result = agent.run(patient, {})
        assert result.success is True
        assert result.data.priority_tier == "GREEN"


class TestTriageSpecialization:
    """Tests for specialization recommendation."""

    def test_cardiology_for_chest_pain(self, agent):
        """Chest pain should recommend Cardiology."""
        patient = make_patient(["chest pain"], age=50)
        result = agent.run(patient, {})
        assert result.data.recommended_specialization == "Cardiology"

    def test_neurology_for_seizure(self, agent):
        """Seizure should recommend Neurology (or Emergency for RED)."""
        patient = make_patient(["seizure"], age=30)
        result = agent.run(patient, {})
        assert result.data.recommended_specialization in ("Neurology", "Emergency Medicine")

    def test_invalid_input(self, agent):
        """Non-Patient input should fail."""
        result = agent.run("not a patient", {})
        assert result.success is False
