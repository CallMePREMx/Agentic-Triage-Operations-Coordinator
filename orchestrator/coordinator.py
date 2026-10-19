"""
Triage Coordinator — Main Orchestrator.

Chains the four agents (Intake → Triage → Operations → Critic) into a
sequential pipeline with shared context. Manages data flow between agents,
handles partial failures, and produces a complete audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents.intake_agent import IntakeAgent
from agents.triage_agent import TriageAgent
from agents.operations_agent import OperationsAgent
from agents.critic_agent import CriticAgent
from config.logging_config import get_agent_logger
from orchestrator.session_manager import TriageSessionManager
from utils.formatters import format_pipeline_summary, format_triage_report


class PipelineResult:
    """
    Complete result of a triage pipeline execution.

    Contains the final outcome, individual agent results, audit trail,
    clarification metadata (if multi-turn interview needed),
    and the pipeline execution summary.
    """

    def __init__(self):
        self.request_id: str = ""
        self.success: bool = False
        self.agent_results: Dict[str, AgentResult] = {}
        self.context: Dict = {}
        self.steps: List[Dict] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.audit_trail: List[Dict] = []
        self.pipeline_summary: str = ""
        self.triage_report: str = ""
        self.confirmation_summary: str = ""
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

        # Multi-turn conversational interview state
        self.session_id: str = ""
        self.needs_clarification: bool = False
        self.clarification_prompt: str = ""
        self.clarification_questions: List[Dict] = []
        self.quick_replies: List[str] = []

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    def to_dict(self) -> dict:
        """Serialize the full pipeline result."""
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "needs_clarification": self.needs_clarification,
            "clarification_prompt": self.clarification_prompt,
            "clarification_questions": self.clarification_questions,
            "quick_replies": self.quick_replies,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
            "steps": self.steps,
            "elapsed_seconds": round(self.elapsed_seconds, 4),
            "patient": (
                self.context.get("patient").to_dict()
                if self.context.get("patient")
                else None
            ),
            "appointment": (
                self.context.get("appointment").to_dict()
                if self.context.get("appointment")
                else None
            ),
            "triage_report": self.triage_report,
            "confirmation_summary": self.confirmation_summary,
            "pipeline_summary": self.pipeline_summary,
            "audit_trail": self.audit_trail,
        }


class TriageCoordinator:
    """
    Main coordinator that orchestrates the 4-agent triage pipeline.

    Pipeline flow:
        User Input → IntakeAgent → TriageAgent → OperationsAgent → CriticAgent → Result

    Each agent receives the output of the previous agent and a shared
    context dictionary for cross-agent communication. Supports multi-turn
    conversational clarification when ambiguous symptoms are presented.
    """

    def __init__(self):
        self.logger = get_agent_logger("Coordinator")
        self.session_manager = TriageSessionManager()

        # Initialize all agents
        self.intake_agent = IntakeAgent()
        self.triage_agent = TriageAgent()
        self.operations_agent = OperationsAgent()
        self.critic_agent = CriticAgent()

        # Pipeline definition (ordered)
        self._pipeline = [
            {
                "agent": self.intake_agent,
                "name": "Intake",
                "input_key": None,         # Uses raw input
                "output_key": "patient",
            },
            {
                "agent": self.triage_agent,
                "name": "Triage",
                "input_key": "patient",    # Takes Patient from context
                "output_key": "patient",   # Returns updated Patient
            },
            {
                "agent": self.operations_agent,
                "name": "Operations",
                "input_key": "patient",    # Takes triaged Patient
                "output_key": "appointment",
            },
            {
                "agent": self.critic_agent,
                "name": "Critic",
                "input_key": "appointment",  # Takes Appointment
                "output_key": "appointment", # Returns validated Appointment
            },
        ]

    def process_request(
        self,
        user_input: Any,
        session_id: Optional[str] = None,
        allow_clarification: bool = False,
        force_triage: bool = False,
    ) -> PipelineResult:
        """
        Run the complete triage pipeline for a patient request.

        Args:
            user_input: Raw text string or structured dictionary from the user.
            session_id: Optional ID of an existing conversational interview session.
            allow_clarification: If True, allows IntakeAgent to trigger follow-up questions.
            force_triage: If True, forces final triage without further follow-ups.

        Returns:
            PipelineResult with the complete outcome or clarification request.
        """
        result = PipelineResult()
        result.request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        result.started_at = datetime.now()

        # Session tracking
        if session_id:
            session = self.session_manager.get_or_create(session_id)
            if isinstance(user_input, str):
                current_input = session.append_user_input(user_input)
            elif isinstance(user_input, dict) and "message" in user_input:
                current_input = session.append_user_input(user_input["message"])
            else:
                current_input = user_input
        else:
            raw_initial = user_input if isinstance(user_input, str) else str(user_input)
            session = self.session_manager.create_session(raw_initial)
            current_input = user_input

        result.session_id = session.session_id

        # Shared context passed through all agents
        context: Dict = {
            "request_id": result.request_id,
            "session_id": session.session_id,
            "started_at": result.started_at.isoformat(),
            "allow_clarification": allow_clarification,
            "force_triage": force_triage,
        }

        self.logger.info(
            "=" * 60 + "\n  Pipeline started: %s (Session: %s)\n" + "=" * 60,
            result.request_id,
            session.session_id,
        )

        for step_num, stage in enumerate(self._pipeline, start=1):
            agent = stage["agent"]
            stage_name = stage["name"]
            input_key = stage["input_key"]

            self.logger.info(
                "─── Step %d: %s Agent ───", step_num, stage_name
            )

            # Determine input for this agent
            if input_key and input_key in context:
                current_input = context[input_key]

            # Run the agent
            agent_result = agent.run(current_input, context)

            # Record the step
            step_record = {
                "step": step_num,
                "agent": f"{stage_name} Agent ({agent.role})",
                "action": agent.description,
                "success": agent_result.success,
                "details": (
                    agent_result.errors[0] if agent_result.errors
                    else f"Completed in {agent_result.metadata.get('elapsed_seconds', 0):.3f}s"
                ),
                "metadata": agent_result.metadata,
            }
            result.steps.append(step_record)
            result.agent_results[stage_name] = agent_result

            # Collect warnings
            result.warnings.extend(agent_result.warnings)

            # Collect audit trail from agent
            result.audit_trail.extend(agent.get_audit_trail())

            # If Intake Agent requires clarification, pause and return questions
            if stage_name == "Intake" and agent_result.metadata.get("clarification_needed"):
                result.needs_clarification = True
                result.clarification_prompt = agent_result.metadata.get("clarification_prompt", "")
                result.clarification_questions = agent_result.metadata.get("clarification_questions", [])
                result.quick_replies = agent_result.metadata.get("quick_replies", [])
                session.set_clarification(
                    result.clarification_prompt,
                    result.clarification_questions,
                    result.quick_replies,
                )
                result.success = True
                result.completed_at = datetime.now()
                result.context = context
                self.logger.info(
                    "Pipeline paused for user clarification [Session=%s].",
                    session.session_id,
                )
                return result

            # Check for failure → halt pipeline
            if not agent_result.success:
                result.errors.extend(agent_result.errors)
                self.logger.error(
                    "Pipeline halted at Step %d (%s): %s",
                    step_num, stage_name, agent_result.errors,
                )
                break

            # Update current input for next stage
            if agent_result.data is not None:
                current_input = agent_result.data

            # Generate triage report after triage stage
            if stage_name == "Triage" and agent_result.data:
                result.triage_report = format_triage_report(agent_result.data)

        # ── Finalize ─────────────────────────────────────────────────
        result.completed_at = datetime.now()
        result.context = context
        result.success = len(result.errors) == 0

        if result.success and not result.needs_clarification:
            session.status = "TRIAGED"
            session.pipeline_result = result.to_dict()

        # Generate pipeline summary
        result.pipeline_summary = format_pipeline_summary(result.steps)

        # Get confirmation summary if available
        if context.get("confirmation_summary"):
            result.confirmation_summary = context["confirmation_summary"]

        self.logger.info(
            "Pipeline %s completed in %.3fs. Success: %s",
            result.request_id,
            result.elapsed_seconds,
            result.success,
        )

        return result

    def get_system_stats(self) -> dict:
        """Get statistics from the mock database."""
        from data.mock_database import MockDatabase
        db = MockDatabase()
        return db.get_statistics()

    def get_all_agents_info(self) -> List[Dict]:
        """Return metadata about all agents in the pipeline."""
        return [
            {
                "name": stage["agent"].name,
                "role": stage["agent"].role,
                "description": stage["agent"].description,
                "step": idx + 1,
            }
            for idx, stage in enumerate(self._pipeline)
        ]
