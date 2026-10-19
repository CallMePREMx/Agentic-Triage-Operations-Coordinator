"""
Tests for Multi-Turn Conversational Clarification & Session Management.

Validates:
- TriageSession and TriageSessionManager state retention
- IntakeAgent clarification question generation on ambiguous inputs
- Multi-turn coordinator interview execution
- Disabling clarification or forcing triage
"""

import pytest
from orchestrator.coordinator import TriageCoordinator
from orchestrator.session_manager import TriageSession, TriageSessionManager
from agents.intake_agent import IntakeAgent


@pytest.fixture
def coordinator():
    """Create a coordinator instance for testing."""
    return TriageCoordinator()


@pytest.fixture
def session_manager():
    """Provide clean session manager."""
    mgr = TriageSessionManager()
    mgr.reset_all()
    return mgr


class TestSessionManager:
    """Tests for TriageSessionManager and TriageSession."""

    def test_create_and_get_session(self, session_manager):
        """Creating a session stores and retrieves by ID."""
        session = session_manager.create_session("Initial patient notes")
        assert session.session_id.startswith("SES-")
        assert session.accumulated_text == "Initial patient notes"
        assert len(session.history) == 1

        retrieved = session_manager.get_session(session.session_id)
        assert retrieved is session

    def test_multi_turn_accumulation(self, session_manager):
        """User responses accumulate into comprehensive context."""
        session = session_manager.create_session("I have chest pain")
        session.append_user_input("It radiates to my left arm")
        session.append_user_input("Started 30 minutes ago")

        assert "chest pain" in session.accumulated_text
        assert "radiates to my left arm" in session.accumulated_text
        assert "30 minutes ago" in session.accumulated_text
        assert len(session.history) == 3

    def test_set_clarification_status(self, session_manager):
        """Recording clarification questions updates session status."""
        session = session_manager.create_session("Headache")
        session.set_clarification(
            "Do you have a stiff neck?",
            [{"id": "q1", "prompt": "Stiff neck?"}],
            ["Yes", "No"],
        )
        assert session.status == "AWAITING_CLARIFICATION"
        assert len(session.clarification_questions) == 1


class TestIntakeAgentClarification:
    """Tests for IntakeAgent's question generation on ambiguous symptoms."""

    def test_chest_pain_ambiguity_generates_question(self):
        """Chest pain without radiation or duration probes for red-flags."""
        agent = IntakeAgent()
        context = {"allow_clarification": True}
        result = agent.run("I am experiencing chest pain", context)

        assert result.success is True
        assert result.metadata.get("clarification_needed") is True
        assert len(result.metadata.get("clarification_questions")) > 0
        prompt = result.metadata.get("clarification_prompt")
        assert "radiate" in prompt.lower() or "breath" in prompt.lower()

    def test_headache_ambiguity_generates_question(self):
        """Headache without duration probes for meningitis/migraine features."""
        agent = IntakeAgent()
        context = {"allow_clarification": True}
        result = agent.run("I have a bad headache", context)

        assert result.success is True
        assert result.metadata.get("clarification_needed") is True
        questions = result.metadata.get("clarification_questions")
        prompts = [q["prompt"].lower() for q in questions]
        assert any("stiff neck" in p or "fever" in p or "long" in p for p in prompts)

    def test_clarification_disabled_bypasses_interview(self):
        """When allow_clarification is False, proceeds with defaults."""
        agent = IntakeAgent()
        context = {"allow_clarification": False}
        result = agent.run("I have chest pain", context)

        assert result.success is True
        assert result.metadata.get("clarification_needed") is not True
        assert result.data is not None
        assert result.data.name.startswith("Patient-")


class TestMultiTurnCoordinatorPipeline:
    """End-to-end tests for multi-turn clinical interview execution."""

    def test_multi_turn_interview_flow(self, coordinator):
        """
        Turn 1: Patient says 'I have chest pain' -> Coordinator returns clarification prompt.
        Turn 2: Patient answers 'Pain radiates to arm for 30 minutes' -> Coordinator finalizes booking.
        """
        # Turn 1
        res1 = coordinator.process_request(
            user_input="I have chest pain",
            allow_clarification=True,
        )
        assert res1.needs_clarification is True
        assert res1.session_id != ""
        assert len(res1.quick_replies) > 0

        # Turn 2: Follow-up answer
        session_id = res1.session_id
        res2 = coordinator.process_request(
            user_input="Pain radiates to left arm and started 30 minutes ago, I am 55 years old",
            session_id=session_id,
            allow_clarification=True,
        )
        assert res2.needs_clarification is False
        assert res2.success is True
        assert res2.context.get("patient").priority_tier == "RED"
        assert res2.context.get("appointment") is not None

    def test_force_triage_bypasses_clarification(self, coordinator):
        """Passing force_triage=True overrides clarification and books immediately."""
        result = coordinator.process_request(
            user_input="I have chest pain",
            allow_clarification=True,
            force_triage=True,
        )
        assert result.needs_clarification is False
        assert result.success is True
        assert result.context.get("appointment") is not None
