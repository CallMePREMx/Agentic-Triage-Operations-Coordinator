"""
Triage Agent (Research Role).

Cross-references extracted patient symptoms against medical guidelines
to compute a severity score and assign a priority tier. Uses age and
duration modifiers, red-flag combination detection, and escalation
factor analysis for realistic clinical triage simulation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agents.base_agent import AgentResult, BaseAgent
from config.settings import PRIORITY_TIERS
from data.medical_guidelines import (
    AGE_SEVERITY_MODIFIERS,
    DURATION_MODIFIERS,
    RED_FLAG_COMBINATIONS,
    SEVERITY_THRESHOLDS,
    SYMPTOM_GUIDELINES,
    get_age_modifier,
    get_duration_modifier,
)
from models.patient import Patient


class TriageAgent(BaseAgent):
    """
    Triage Agent — the second agent in the pipeline.

    Responsibilities:
    1. Look up each symptom in the medical guidelines.
    2. Compute a base severity score from symptom severities.
    3. Apply age and duration modifiers.
    4. Check for red-flag symptom combinations (auto-escalate to RED).
    5. Check for escalation factors present across symptoms.
    6. Map the final score to a priority tier.
    7. Recommend a medical specialization.
    """

    def __init__(self):
        super().__init__(
            name="TriageAgent",
            role="Research",
            description="Cross-references symptoms against medical guidelines for priority assignment.",
        )

    def process(self, input_data: Any, context: Dict) -> AgentResult:
        """
        Perform triage assessment on the patient.

        Args:
            input_data: Patient object (from IntakeAgent).
            context: Shared pipeline context.

        Returns:
            AgentResult with triaged Patient (priority + severity assigned).
        """
        if not isinstance(input_data, Patient):
            return AgentResult(
                success=False,
                errors=["TriageAgent expected a Patient object."],
            )

        patient = input_data
        warnings = []
        notes = []

        self.logger.info(
            "Starting triage for %s (Age: %d, Symptoms: %s)",
            patient.patient_id, patient.age, patient.symptoms,
        )

        # ── Step 1: Symptom Lookup & Base Severity ───────────────────
        symptom_scores, symptom_details = self._lookup_symptoms(patient.symptoms)

        if not symptom_scores:
            # No recognized symptoms — assign GREEN by default
            patient.priority_tier = "GREEN"
            patient.severity_score = 0.2
            patient.recommended_specialization = "General Medicine"
            notes.append("No symptoms matched the guidelines database. Assigned default GREEN.")
            patient.triage_notes = notes
            context["patient"] = patient
            return AgentResult(
                success=True,
                data=patient,
                warnings=["No symptoms matched medical guidelines."],
                metadata={"triage_method": "default_fallback"},
            )

        # Base severity = weighted average (highest symptom has more influence)
        base_severity = self._compute_base_severity(symptom_scores)
        notes.append(f"Base severity from {len(symptom_scores)} symptom(s): {base_severity:.3f}")
        self.logger.info("Base severity score: %.3f", base_severity)

        # ── Step 2: Red-Flag Combination Check ───────────────────────
        red_flag_hit, red_flag_reason = self._check_red_flags(patient.symptoms)
        if red_flag_hit:
            notes.append(f"RED FLAG TRIGGERED: {red_flag_reason}")
            self.logger.warning("RED FLAG detected: %s", red_flag_reason)
            base_severity = max(base_severity, 0.90)

        # ── Step 3: Escalation Factor Analysis ───────────────────────
        escalation_boost = self._check_escalation_factors(patient.symptoms, symptom_details)
        if escalation_boost > 0:
            notes.append(f"Escalation factor boost: +{escalation_boost:.3f}")
            base_severity += escalation_boost
            self.logger.info("Escalation boost applied: +%.3f", escalation_boost)

        # ── Step 4: Age Modifier ─────────────────────────────────────
        age_mod, age_category, age_note = get_age_modifier(patient.age)
        modified_severity = base_severity * age_mod
        notes.append(f"Age modifier ({age_category}, x{age_mod}): {age_note}")
        self.logger.info("Age modifier: x%.2f (%s)", age_mod, age_category)

        # ── Step 5: Duration Modifier ────────────────────────────────
        duration_mod = self._parse_duration_modifier(patient.symptom_duration)
        modified_severity *= duration_mod
        notes.append(f"Duration modifier (x{duration_mod}): based on '{patient.symptom_duration}'")
        self.logger.info("Duration modifier: x%.2f", duration_mod)

        # Clamp to [0, 1]
        final_score = min(max(modified_severity, 0.0), 1.0)
        notes.append(f"Final severity score: {final_score:.3f}")

        # ── Step 6: Map to Priority Tier ─────────────────────────────
        priority_tier = self._score_to_tier(final_score)
        notes.append(f"Assigned priority tier: {priority_tier} ({PRIORITY_TIERS[priority_tier]['label']})")
        self.logger.info("Priority tier: %s (score=%.3f)", priority_tier, final_score)

        # ── Step 7: Recommend Specialization ─────────────────────────
        specialization = self._recommend_specialization(symptom_details, priority_tier, patient.age)
        notes.append(f"Recommended specialization: {specialization}")

        # ── Update Patient ───────────────────────────────────────────
        patient.priority_tier = priority_tier
        patient.severity_score = round(final_score, 4)
        patient.recommended_specialization = specialization
        patient.triage_notes = notes

        # ── Update Context ───────────────────────────────────────────
        context["patient"] = patient
        context["triage_complete"] = True

        return AgentResult(
            success=True,
            data=patient,
            warnings=warnings,
            metadata={
                "severity_score": final_score,
                "priority_tier": priority_tier,
                "specialization": specialization,
                "red_flag_detected": red_flag_hit,
                "symptom_count_matched": len(symptom_scores),
                "age_modifier": age_mod,
                "duration_modifier": duration_mod,
            },
        )

    # ─── Private Helper Methods ──────────────────────────────────────────

    def _lookup_symptoms(
        self, symptoms: List[str]
    ) -> Tuple[List[float], List[dict]]:
        """Look up each symptom in the guidelines and return scores + details."""
        scores = []
        details = []
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            if symptom_lower in SYMPTOM_GUIDELINES:
                guideline = SYMPTOM_GUIDELINES[symptom_lower]
                scores.append(guideline["base_severity"])
                details.append({
                    "symptom": symptom_lower,
                    **guideline,
                })
                self.logger.debug(
                    "Symptom '%s' matched: severity=%.2f, hint=%s",
                    symptom, guideline["base_severity"], guideline["priority_hint"],
                )
            else:
                self.logger.debug("Symptom '%s' not in guidelines.", symptom)
        return scores, details

    def _compute_base_severity(self, scores: List[float]) -> float:
        """
        Compute base severity from individual symptom scores.
        Uses weighted approach: max symptom contributes 60%, average of rest 40%.
        """
        if not scores:
            return 0.0
        if len(scores) == 1:
            return scores[0]

        sorted_scores = sorted(scores, reverse=True)
        max_score = sorted_scores[0]
        rest_avg = sum(sorted_scores[1:]) / len(sorted_scores[1:])

        # Multiple symptoms compound severity
        multi_symptom_bonus = min(0.05 * (len(scores) - 1), 0.15)

        return (0.6 * max_score) + (0.4 * rest_avg) + multi_symptom_bonus

    def _check_red_flags(
        self, symptoms: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Check if the patient's symptoms match any red-flag combination."""
        patient_symptoms_lower = {s.lower() for s in symptoms}

        for combo in RED_FLAG_COMBINATIONS:
            if combo["symptoms"].issubset(patient_symptoms_lower):
                return True, combo["reason"]

        return False, None

    def _check_escalation_factors(
        self, symptoms: List[str], symptom_details: List[dict]
    ) -> float:
        """
        Check if any symptom's escalation factors are present
        in the patient's other symptoms. Returns a boost value.
        """
        patient_symptoms_lower = {s.lower() for s in symptoms}
        total_boost = 0.0

        for detail in symptom_details:
            escalation_factors = detail.get("escalation_factors", [])
            for factor in escalation_factors:
                if factor.lower() in patient_symptoms_lower:
                    # Each matched escalation factor adds a small boost
                    total_boost += 0.05
                    self.logger.debug(
                        "Escalation factor '%s' found for symptom '%s'",
                        factor, detail["symptom"],
                    )

        # Cap the escalation boost
        return min(total_boost, 0.20)

    def _parse_duration_modifier(self, duration: str) -> float:
        """Extract the time unit from the duration string and get its modifier."""
        if not duration or duration == "unknown":
            return 1.0

        duration_lower = duration.lower()
        for unit in ["minutes", "minute", "hours", "hour", "days", "day",
                      "weeks", "week", "months", "month"]:
            if unit in duration_lower:
                return get_duration_modifier(unit)

        return 1.0

    def _score_to_tier(self, score: float) -> str:
        """Map a severity score to a priority tier using thresholds."""
        for tier in ["RED", "ORANGE", "YELLOW", "GREEN", "BLUE"]:
            if score >= SEVERITY_THRESHOLDS[tier]:
                return tier
        return "BLUE"

    def _recommend_specialization(
        self, symptom_details: List[dict], priority_tier: str, age: int = 30
    ) -> str:
        """
        Recommend a specialization based on symptom guidelines and patient age.

        Priority: Emergency Medicine for RED, else Pediatrics for minors (<18)
        with general symptoms, else most common specialization among the patient's symptoms.
        """
        if priority_tier == "RED":
            # Check if there's a specific specialization for the red symptoms
            for detail in symptom_details:
                if detail.get("priority_hint") == "RED":
                    return detail["specialization"]
            return "Emergency Medicine"

        # Count specialization occurrences
        spec_counts: Dict[str, int] = {}
        for detail in symptom_details:
            spec = detail["specialization"]
            spec_counts[spec] = spec_counts.get(spec, 0) + 1

        # For pediatric patients (<18), route general medical issues to Pediatrics
        if age < 18:
            if not spec_counts or "General Medicine" in spec_counts or "Pediatrics" in spec_counts:
                return "Pediatrics"

        if spec_counts:
            return max(spec_counts, key=spec_counts.get)

        return "Pediatrics" if age < 18 else "General Medicine"
