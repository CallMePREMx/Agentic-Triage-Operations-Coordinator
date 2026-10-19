"""
Tests for the Intake Agent.

Validates free-text parsing, structured input handling, edge cases,
and patient model creation.
"""

import sys
import os
import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.intake_agent import IntakeAgent
from models.patient import Patient


@pytest.fixture
def agent():
    return IntakeAgent()


class TestIntakeAgentFreeText:
    """Tests for free-text (chat) input parsing."""

    def test_full_description(self, agent):
        """Test parsing a complete patient description."""
        text = (
            "My name is Sarah Khan, I'm 45 years old. "
            "I've been having chest pain and shortness of breath for 2 hours."
        )
        result = agent.run(text, {})
        assert result.success is True
        patient = result.data
        assert isinstance(patient, Patient)
        assert patient.age == 45
        assert "chest pain" in patient.symptoms
        assert "shortness of breath" in patient.symptoms
        assert "2 hours" in patient.symptom_duration

    def test_minimal_description(self, agent):
        """Test parsing with minimal info — just symptoms."""
        text = "I have a severe headache and fever for 3 days."
        result = agent.run(text, {})
        assert result.success is True
        assert "headache" in result.data.symptoms or "severe headache" in result.data.symptoms
        assert "fever" in result.data.symptoms

    def test_no_symptoms_fails(self, agent):
        """Test that input with no recognizable symptoms fails."""
        text = "Hello, I would like to schedule an appointment please."
        result = agent.run(text, {})
        assert result.success is False
        assert any("symptom" in e.lower() for e in result.errors)

    def test_age_extraction_variants(self, agent):
        """Test various age formats."""
        texts = [
            ("I am 30 and have a headache for 1 day", 30),
            ("Patient is 72 years old with back pain for 2 weeks", 72),
            ("age 5 with fever lasting 2 days", 5),
        ]
        for text, expected_age in texts:
            result = agent.run(text, {})
            assert result.success is True
            assert result.data.age == expected_age, f"Failed for: {text}"


class TestIntakeAgentStructured:
    """Tests for structured (form) input."""

    def test_dict_input(self, agent):
        """Test structured dictionary input."""
        data = {
            "name": "John Smith",
            "age": 50,
            "symptoms": "chest pain, nausea",
            "symptom_duration": "1 hour",
            "gender": "Male",
        }
        result = agent.run(data, {})
        assert result.success is True
        assert result.data.name == "John Smith"
        assert result.data.age == 50
        assert "chest pain" in result.data.symptoms
        assert "nausea" in result.data.symptoms

    def test_list_symptoms(self, agent):
        """Test symptoms as a list."""
        data = {
            "name": "Jane",
            "age": 35,
            "symptoms": ["headache", "fever"],
            "duration": "2 days",
        }
        result = agent.run(data, {})
        assert result.success is True
        assert len(result.data.symptoms) == 2

    def test_context_updated(self, agent):
        """Test that the pipeline context is properly updated."""
        context = {}
        data = {
            "name": "Test",
            "age": 25,
            "symptoms": ["cough"],
            "duration": "3 days",
        }
        agent.run(data, context)
        assert "patient" in context
        assert isinstance(context["patient"], Patient)

    def test_invalid_input_type(self, agent):
        """Test that invalid input types are rejected."""
        result = agent.run(12345, {})
        assert result.success is False
