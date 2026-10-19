"""
Intake Agent (Planner Role).

Parses free-text or structured user input to extract patient data:
name, age, symptoms, duration, contact information. Validates
completeness and builds a Patient model for downstream agents.
"""

from __future__ import annotations

from typing import Any, Dict

from agents.base_agent import AgentResult, BaseAgent
from models.patient import Patient
from utils.nlp_parser import parse_patient_input


class IntakeAgent(BaseAgent):
    """
    Intake Agent — the first agent in the triage pipeline.

    Responsibilities:
    1. Parse raw user input (chat/voice text) into structured fields.
    2. Create a Patient model with the extracted data.
    3. Identify missing fields and flag extraction confidence.
    4. Pass the structured Patient to the next agent via context.
    """

    def __init__(self):
        super().__init__(
            name="IntakeAgent",
            role="Planner",
            description="Parses user input to extract structured patient data.",
        )

    def process(self, input_data: Any, context: Dict) -> AgentResult:
        """
        Parse patient input and build a structured Patient record.

        Args:
            input_data: Raw text string from the user, OR a dictionary
                        with pre-structured fields.
            context: Shared pipeline context dictionary.

        Returns:
            AgentResult with Patient object as data.
        """
        warnings = []
        errors = []

        # ── Step 1: Parse Input ──────────────────────────────────────
        if isinstance(input_data, str):
            self.logger.info("Parsing free-text input (%d chars).", len(input_data))
            parsed = parse_patient_input(input_data)
        elif isinstance(input_data, dict):
            self.logger.info("Received structured input.")
            parsed = self._normalize_structured_input(input_data)
        else:
            return AgentResult(
                success=False,
                errors=["Invalid input type. Expected string or dictionary."],
            )

        self.logger.info(
            "Extracted fields — Name: %s, Age: %s, Symptoms: %s, Duration: %s, Confidence: %s",
            parsed.get("name"),
            parsed.get("age"),
            parsed.get("symptoms"),
            parsed.get("symptom_duration"),
            parsed.get("extraction_confidence"),
        )

        # ── Step 2: Clinical Clarification Check (Agentic Interview) ──
        allow_clarification = context.get("allow_clarification", False)
        force_triage = context.get("force_triage", False)
        raw_str = parsed.get("raw_input", str(input_data))

        if allow_clarification and not force_triage and parsed.get("symptoms"):
            clarification_questions = self.generate_clarification_questions(parsed, raw_str)
            if clarification_questions:
                primary_q = clarification_questions[0]
                quick_replies = primary_q.get("options", [])
                self.logger.info("IntakeAgent requests clinical clarification: %s", primary_q["prompt"])
                context["clarification_needed"] = True
                context["clarification_questions"] = clarification_questions
                context["clarification_prompt"] = primary_q["prompt"]
                context["quick_replies"] = quick_replies
                context["partial_patient"] = parsed

                return AgentResult(
                    success=True,
                    data=None,
                    warnings=warnings + ["Clinical clarification requested before doctor scheduling."],
                    metadata={
                        "clarification_needed": True,
                        "clarification_questions": clarification_questions,
                        "clarification_prompt": primary_q["prompt"],
                        "quick_replies": quick_replies,
                        "extraction_confidence": parsed.get("extraction_confidence", 0),
                        "parsed_so_far": parsed,
                    },
                )

        # ── Step 3: Handle Missing Critical Fields ───────────────────
        missing = parsed.get("missing_fields", [])

        # Name fallback
        if parsed.get("name") is None:
            parsed["name"] = f"Patient-{context.get('request_id', 'Unknown')[:8]}"
            warnings.append("Patient name not detected; auto-generated placeholder.")

        # Age fallback
        if parsed.get("age") is None:
            parsed["age"] = 30  # Default assumption
            warnings.append("Patient age not detected; defaulting to 30.")

        # Symptoms — critical, cannot proceed without
        if not parsed.get("symptoms"):
            errors.append(
                "No symptoms could be extracted from the input. "
                "Please describe the patient's symptoms."
            )
            return AgentResult(success=False, errors=errors, warnings=warnings)

        # Duration fallback
        if parsed.get("symptom_duration") is None:
            parsed["symptom_duration"] = "unknown"
            warnings.append("Symptom duration not detected; marked as 'unknown'.")

        # ── Step 4: Build Patient Model ──────────────────────────────
        patient = Patient(
            name=parsed["name"],
            age=parsed["age"],
            symptoms=parsed["symptoms"],
            symptom_duration=parsed["symptom_duration"],
            contact=parsed.get("contact", ""),
            gender=parsed.get("gender", "Unknown"),
            raw_input=parsed.get("raw_input", str(input_data)),
        )

        # ── Step 5: Update Pipeline Context ──────────────────────────
        context["patient"] = patient
        context["extraction_confidence"] = parsed.get("extraction_confidence", 0.0)
        context["missing_fields"] = missing

        self.logger.info(
            "Patient record created: %s (Confidence: %.0f%%)",
            patient.patient_id,
            parsed.get("extraction_confidence", 0) * 100,
        )

        return AgentResult(
            success=True,
            data=patient,
            warnings=warnings,
            metadata={
                "extraction_confidence": parsed.get("extraction_confidence", 0),
                "missing_fields": missing,
                "symptom_count": len(patient.symptoms),
            },
        )

    def generate_clarification_questions(
        self, parsed: Dict[str, Any], raw_text: str
    ) -> List[Dict[str, Any]]:
        """
        Generate targeted clinical follow-up questions to resolve ambiguities
        or probe for critical red-flag escalation factors.
        """
        questions = []
        raw_lower = raw_text.lower()
        symptoms = [s.lower() for s in parsed.get("symptoms", [])]

        # 1. Symptom-specific escalation factor probes
        if "chest pain" in symptoms:
            has_radiation = any(w in raw_lower for w in ["arm", "jaw", "neck", "back", "radiat"])
            has_breathing = any(w in raw_lower for w in ["breath", "shortness", "dyspnea"])
            if not (has_radiation or has_breathing):
                questions.append({
                    "id": "chest_pain_features",
                    "field": "symptoms",
                    "prompt": "Does the chest pain radiate to your arm, neck, or jaw, or are you having shortness of breath?",
                    "options": [
                        "Pain radiates to left arm or jaw",
                        "Shortness of breath present",
                        "No radiation or breathing trouble",
                        "Sharp pain when coughing or inhaling",
                    ],
                })

        if "headache" in symptoms and "severe headache" not in symptoms:
            has_neuro = any(w in raw_lower for w in ["stiff neck", "neck", "fever", "thunderclap", "vision"])
            if not has_neuro:
                questions.append({
                    "id": "headache_features",
                    "field": "symptoms",
                    "prompt": "Is the headache accompanied by a stiff neck, high fever, or sudden thunderclap onset?",
                    "options": [
                        "Accompanied by stiff neck and fever",
                        "Sudden thunderclap onset",
                        "Sensitive to light (migraine-like)",
                        "Standard dull or throbbing ache",
                    ],
                })

        if "abdominal pain" in symptoms:
            has_gi_flags = any(w in raw_lower for w in ["vomit", "fever", "blood", "stool", "rigid"])
            if not has_gi_flags:
                questions.append({
                    "id": "abdominal_features",
                    "field": "symptoms",
                    "prompt": "Do you have any fever, vomiting, or blood in stool with this abdominal pain?",
                    "options": [
                        "Fever and vomiting present",
                        "Severe sharp tenderness",
                        "Mild cramping, no vomiting",
                    ],
                })

        if "dizziness" in symptoms:
            has_neuro = any(w in raw_lower for w in ["faint", "weak", "slur", "face", "vision"])
            if not has_neuro:
                questions.append({
                    "id": "dizziness_features",
                    "field": "symptoms",
                    "prompt": "Have you experienced fainting, muscle weakness, or slurred speech?",
                    "options": [
                        "Feeling faint or weak",
                        "Slurred speech present",
                        "No, just mild lightheadedness",
                    ],
                })

        # 2. Missing Duration Probe (if duration is unknown)
        if not parsed.get("symptom_duration") or parsed.get("symptom_duration") == "unknown":
            questions.append({
                "id": "duration_probe",
                "field": "duration",
                "prompt": "How long have you been experiencing these symptoms?",
                "options": [
                    "Started less than 1 hour ago (Acute)",
                    "A few hours ago",
                    "1 to 3 days ago",
                    "More than 1 week ago (Chronic)",
                ],
            })

        # 3. Missing Age Probe (if age was not detected)
        if parsed.get("age") is None:
            questions.append({
                "id": "age_probe",
                "field": "age",
                "prompt": "What is the patient's approximate age category?",
                "options": [
                    "Under 18 (Pediatric)",
                    "18 - 59 (Adult)",
                    "60+ (Senior)",
                ],
            })

        return questions

    def _normalize_structured_input(self, data: dict) -> dict:
        """
        Normalize a pre-structured dictionary input into the expected format.

        Supports both direct field specification and chat-like payloads.
        """
        # If it looks like a structured form submission
        symptoms = data.get("symptoms", [])
        if isinstance(symptoms, str):
            symptoms = [s.strip() for s in symptoms.split(",") if s.strip()]

        return {
            "name": data.get("name"),
            "age": data.get("age"),
            "gender": data.get("gender", "Unknown"),
            "symptoms": symptoms,
            "symptom_duration": data.get("symptom_duration") or data.get("duration"),
            "contact": data.get("contact") or data.get("phone") or data.get("email"),
            "raw_input": str(data),
            "extraction_confidence": 1.0 if data.get("name") and data.get("age") else 0.8,
            "missing_fields": [],
        }
