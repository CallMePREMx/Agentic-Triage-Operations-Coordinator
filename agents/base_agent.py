"""
Base Agent abstract class.

Defines the contract all agents must follow: a unified `process()` method,
built-in logging, and an audit trail for every action taken. This ensures
consistent behavior and traceability across the agent pipeline.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List

from config.logging_config import get_agent_logger


class AgentResult:
    """
    Standardized result returned by every agent.

    Attributes:
        success: Whether the agent completed its task successfully.
        data: The primary output payload (varies per agent).
        errors: List of error messages encountered.
        warnings: List of non-fatal warning messages.
        metadata: Extra context (timings, confidence scores, etc.).
    """

    def __init__(
        self,
        success: bool = True,
        data: Any = None,
        errors: List[str] = None,
        warnings: List[str] = None,
        metadata: Dict = None,
    ):
        self.success = success
        self.data = data
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """Serialize result for transport/storage."""
        return {
            "success": self.success,
            "data": self.data if not hasattr(self.data, "to_dict") else self.data.to_dict(),
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the triage pipeline.

    Provides:
    - Unified `run()` wrapper with timing and error handling
    - Abstract `process()` for subclass-specific logic
    - Built-in audit trail
    - Per-agent logging
    """

    def __init__(self, name: str, role: str, description: str = ""):
        self.name = name
        self.role = role
        self.description = description
        self.logger = get_agent_logger(name)
        self.audit_trail: List[Dict] = []

    def run(self, input_data: Any, context: Dict = None) -> AgentResult:
        """
        Execute the agent with timing, logging, and error handling.

        This is the public entry point. It wraps the subclass-specific
        `process()` method with cross-cutting concerns.

        Args:
            input_data: The input payload for this agent.
            context: Shared context dictionary passed through the pipeline.

        Returns:
            AgentResult with the processing outcome.
        """
        if context is None:
            context = {}
        start_time = time.time()
        self.logger.info("▶ %s [%s] started processing.", self.name, self.role)

        try:
            result = self.process(input_data, context)
            elapsed = time.time() - start_time

            # Record audit entry
            audit_entry = {
                "agent": self.name,
                "role": self.role,
                "timestamp": datetime.now().isoformat(),
                "elapsed_seconds": round(elapsed, 4),
                "success": result.success,
                "errors": result.errors,
                "warnings": result.warnings,
            }
            self.audit_trail.append(audit_entry)

            # Log outcome
            if result.success:
                self.logger.info(
                    "✓ %s completed in %.3fs.", self.name, elapsed
                )
            else:
                self.logger.warning(
                    "✗ %s completed with errors in %.3fs: %s",
                    self.name, elapsed, result.errors,
                )

            # Attach timing metadata
            result.metadata["elapsed_seconds"] = round(elapsed, 4)
            result.metadata["agent_name"] = self.name
            result.metadata["agent_role"] = self.role

            return result

        except Exception as exc:
            elapsed = time.time() - start_time
            self.logger.error(
                "✗ %s failed after %.3fs: %s", self.name, elapsed, str(exc),
                exc_info=True,
            )
            self.audit_trail.append({
                "agent": self.name,
                "role": self.role,
                "timestamp": datetime.now().isoformat(),
                "elapsed_seconds": round(elapsed, 4),
                "success": False,
                "errors": [str(exc)],
                "warnings": [],
            })
            return AgentResult(
                success=False,
                errors=[f"{self.name} encountered an error: {str(exc)}"],
                metadata={"elapsed_seconds": round(elapsed, 4)},
            )

    @abstractmethod
    def process(self, input_data: Any, context: Dict) -> AgentResult:
        """
        Subclass-specific processing logic.

        Args:
            input_data: The input payload.
            context: Shared pipeline context.

        Returns:
            AgentResult with processing outcome.
        """
        raise NotImplementedError

    def get_audit_trail(self) -> List[Dict]:
        """Return the complete audit trail for this agent."""
        return self.audit_trail.copy()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, role={self.role!r})"
