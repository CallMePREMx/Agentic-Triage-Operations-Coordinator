"""
Tests for the Triage Coordinator (Orchestrator).

Validates end-to-end pipeline execution with various input scenarios.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.mock_database import MockDatabase
from orchestrator.coordinator import TriageCoordinator, PipelineResult


@pytest.fixture(autouse=True)
def reset_db():
    """Reset the database before each test."""
    db = MockDatabase()
    db.reset()
    yield


@pytest.fixture
def coordinator():
    return TriageCoordinator()


class TestPipelineEndToEnd:
    """End-to-end pipeline tests."""

    def test_emergency_case(self, coordinator):
        """Full pipeline with emergency symptoms."""
        text = (
            "My name is Sarah Khan, 55 years old female. "
            "Severe chest pain and shortness of breath for 30 minutes."
        )
        result = coordinator.process_request(text)
        assert isinstance(result, PipelineResult)
        assert result.success is True
        assert len(result.steps) == 4
        assert result.context["patient"].priority_tier == "RED"
        assert result.context["appointment"] is not None

    def test_routine_case(self, coordinator):
        """Full pipeline with routine symptoms."""
        text = "I'm John, 28 years old. I have a cough and sore throat for 5 days."
        result = coordinator.process_request(text)
        assert result.success is True
        assert result.context["patient"].priority_tier in ("GREEN", "BLUE", "YELLOW")

    def test_structured_input(self, coordinator):
        """Full pipeline with structured (form) input."""
        data = {
            "name": "Emily Davis",
            "age": 35,
            "symptoms": "headache, fever",
            "symptom_duration": "2 days",
            "gender": "Female",
        }
        result = coordinator.process_request(data)
        assert result.success is True
        assert result.context["patient"].name == "Emily Davis"

    def test_pediatric_case(self, coordinator):
        """Pipeline with pediatric patient should apply age modifier."""
        text = "My son is 3 years old. He has high fever and crying inconsolably for 1 day."
        result = coordinator.process_request(text)
        assert result.success is True
        # Young child with fever should be at least YELLOW
        assert result.context["patient"].priority_tier in ("RED", "ORANGE", "YELLOW")

    def test_no_symptoms_halts_pipeline(self, coordinator):
        """Pipeline should halt at intake if no symptoms are found."""
        text = "Hello, I want to make an appointment for a check-up."
        result = coordinator.process_request(text)
        assert result.success is False
        assert len(result.steps) == 1  # Only intake ran
        assert result.steps[0]["success"] is False


class TestPipelineResult:
    """Tests for the PipelineResult object."""

    def test_result_serialization(self, coordinator):
        """PipelineResult.to_dict() should be JSON-serializable."""
        import json
        result = coordinator.process_request({
            "name": "Test",
            "age": 30,
            "symptoms": ["headache"],
            "duration": "1 day",
        })
        data = result.to_dict()
        json_str = json.dumps(data)  # Should not raise
        assert "request_id" in data
        assert "steps" in data

    def test_elapsed_time_tracked(self, coordinator):
        """Pipeline should track execution time."""
        result = coordinator.process_request({
            "name": "Test",
            "age": 30,
            "symptoms": ["fever"],
            "duration": "2 days",
        })
        assert result.elapsed_seconds > 0

    def test_audit_trail_populated(self, coordinator):
        """Audit trail should contain entries from all agents."""
        result = coordinator.process_request({
            "name": "Test",
            "age": 30,
            "symptoms": ["back pain"],
            "duration": "1 week",
        })
        assert len(result.audit_trail) >= 4  # One per agent


class TestSystemStats:
    """Tests for system statistics."""

    def test_stats_after_pipeline(self, coordinator):
        """Stats should reflect pipeline activity."""
        coordinator.process_request({
            "name": "Test",
            "age": 30,
            "symptoms": ["headache"],
            "duration": "1 day",
        })
        stats = coordinator.get_system_stats()
        assert stats["total_patients"] >= 1
        assert stats["total_appointments"] >= 1
