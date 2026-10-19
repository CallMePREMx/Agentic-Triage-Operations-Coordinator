"""
Medical guidelines for symptom-based triage.

Contains dummy but realistic medical guidelines that map symptoms to
priority tiers and recommended specializations. Used by the Triage Agent
to assign severity scores and priority tiers.

Guidelines structure:
    Each symptom keyword maps to a dictionary containing:
    - base_severity: float (0.0-1.0) indicating inherent danger
    - priority_hint: suggested priority tier
    - specialization: recommended medical specialization
    - escalation_factors: conditions that increase severity
    - red_flags: combinations requiring immediate escalation to RED
"""

# ─── Symptom → Clinical Mapping ──────────────────────────────────────────────

SYMPTOM_GUIDELINES = {
    # ── Cardiovascular ────────────────────────────────────────────────────
    "chest pain": {
        "base_severity": 0.85,
        "priority_hint": "RED",
        "specialization": "Cardiology",
        "escalation_factors": ["shortness of breath", "radiating pain", "sweating", "nausea"],
        "description": "May indicate myocardial infarction or angina.",
    },
    "palpitations": {
        "base_severity": 0.50,
        "priority_hint": "YELLOW",
        "specialization": "Cardiology",
        "escalation_factors": ["dizziness", "fainting", "chest pain"],
        "description": "Irregular heartbeat, may indicate arrhythmia.",
    },
    "high blood pressure": {
        "base_severity": 0.55,
        "priority_hint": "YELLOW",
        "specialization": "Cardiology",
        "escalation_factors": ["headache", "blurred vision", "chest pain"],
        "description": "Hypertensive episode requiring monitoring.",
    },

    # ── Neurological ─────────────────────────────────────────────────────
    "severe headache": {
        "base_severity": 0.70,
        "priority_hint": "ORANGE",
        "specialization": "Neurology",
        "escalation_factors": ["stiff neck", "vision changes", "confusion", "vomiting"],
        "description": "Could indicate migraine, meningitis, or stroke.",
    },
    "headache": {
        "base_severity": 0.30,
        "priority_hint": "GREEN",
        "specialization": "General Medicine",
        "escalation_factors": ["fever", "stiff neck", "vision changes"],
        "description": "Common headache, usually benign.",
    },
    "dizziness": {
        "base_severity": 0.45,
        "priority_hint": "YELLOW",
        "specialization": "Neurology",
        "escalation_factors": ["fainting", "slurred speech", "weakness"],
        "description": "May indicate vertigo, dehydration, or neurological issue.",
    },
    "seizure": {
        "base_severity": 0.90,
        "priority_hint": "RED",
        "specialization": "Neurology",
        "escalation_factors": ["loss of consciousness", "fever", "head injury"],
        "description": "Requires immediate neurological evaluation.",
    },
    "numbness": {
        "base_severity": 0.55,
        "priority_hint": "YELLOW",
        "specialization": "Neurology",
        "escalation_factors": ["weakness", "slurred speech", "facial drooping"],
        "description": "Could indicate nerve damage or stroke.",
    },
    "confusion": {
        "base_severity": 0.75,
        "priority_hint": "ORANGE",
        "specialization": "Neurology",
        "escalation_factors": ["fever", "head injury", "slurred speech"],
        "description": "Altered mental status requires urgent evaluation.",
    },
    "facial drooping": {
        "base_severity": 0.85,
        "priority_hint": "RED",
        "specialization": "Neurology",
        "escalation_factors": ["slurred speech", "numbness", "weakness"],
        "description": "Unilateral facial weakness; hallmark sign of stroke (FAST).",
    },
    "slurred speech": {
        "base_severity": 0.85,
        "priority_hint": "RED",
        "specialization": "Neurology",
        "escalation_factors": ["facial drooping", "numbness", "confusion"],
        "description": "Acute dysarthria; potential cerebrovascular accident / stroke.",
    },
    "stiff neck": {
        "base_severity": 0.70,
        "priority_hint": "ORANGE",
        "specialization": "Neurology",
        "escalation_factors": ["fever", "severe headache", "confusion"],
        "description": "Nuchal rigidity; indicator of possible meningitis or SAH.",
    },
    "loss of consciousness": {
        "base_severity": 0.95,
        "priority_hint": "RED",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["head injury", "bleeding", "seizure"],
        "description": "Syncope or coma; immediate life threat.",
    },
    "swelling of throat": {
        "base_severity": 0.90,
        "priority_hint": "RED",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["difficulty breathing", "wheezing", "rash"],
        "description": "Acute angioedema or anaphylaxis; airway compromise risk.",
    },
    "vomiting blood": {
        "base_severity": 0.85,
        "priority_hint": "RED",
        "specialization": "Gastroenterology",
        "escalation_factors": ["dizziness", "black stool", "abdominal pain"],
        "description": "Hematemesis; acute upper gastrointestinal hemorrhage.",
    },
    "high fever": {
        "base_severity": 0.60,
        "priority_hint": "ORANGE",
        "specialization": "General Medicine",
        "escalation_factors": ["confusion", "stiff neck", "rash", "convulsions"],
        "description": "High fever (>39C / 102F) requiring rapid clinical evaluation.",
    },
    "bleeding": {
        "base_severity": 0.65,
        "priority_hint": "ORANGE",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["dizziness", "loss of consciousness", "weakness"],
        "description": "Active bleeding requiring immediate hemostatic control.",
    },

    # ── Respiratory ──────────────────────────────────────────────────────
    "shortness of breath": {
        "base_severity": 0.75,
        "priority_hint": "ORANGE",
        "specialization": "Pulmonology",
        "escalation_factors": ["chest pain", "wheezing", "cyanosis", "fever"],
        "description": "May indicate asthma, pneumonia, or PE.",
    },
    "cough": {
        "base_severity": 0.25,
        "priority_hint": "GREEN",
        "specialization": "General Medicine",
        "escalation_factors": ["blood", "fever", "shortness of breath", "weight loss"],
        "description": "Common symptom, usually viral.",
    },
    "wheezing": {
        "base_severity": 0.55,
        "priority_hint": "YELLOW",
        "specialization": "Pulmonology",
        "escalation_factors": ["shortness of breath", "chest tightness", "cyanosis"],
        "description": "Indicates bronchospasm or airway obstruction.",
    },
    "difficulty breathing": {
        "base_severity": 0.80,
        "priority_hint": "RED",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["chest pain", "cyanosis", "altered consciousness"],
        "description": "Acute respiratory distress, potentially life-threatening.",
    },

    # ── Gastrointestinal ─────────────────────────────────────────────────
    "abdominal pain": {
        "base_severity": 0.50,
        "priority_hint": "YELLOW",
        "specialization": "Gastroenterology",
        "escalation_factors": ["vomiting blood", "severe tenderness", "fever", "rigidity"],
        "description": "Could range from gastritis to surgical emergency.",
    },
    "nausea": {
        "base_severity": 0.25,
        "priority_hint": "GREEN",
        "specialization": "General Medicine",
        "escalation_factors": ["vomiting", "blood", "severe pain", "dehydration"],
        "description": "Common symptom with many possible causes.",
    },
    "vomiting": {
        "base_severity": 0.40,
        "priority_hint": "YELLOW",
        "specialization": "Gastroenterology",
        "escalation_factors": ["blood", "severe dehydration", "head injury"],
        "description": "May lead to dehydration if persistent.",
    },
    "diarrhea": {
        "base_severity": 0.30,
        "priority_hint": "GREEN",
        "specialization": "Gastroenterology",
        "escalation_factors": ["blood", "severe dehydration", "fever", "weight loss"],
        "description": "Usually self-limiting, monitor for dehydration.",
    },
    "blood in stool": {
        "base_severity": 0.70,
        "priority_hint": "ORANGE",
        "specialization": "Gastroenterology",
        "escalation_factors": ["dizziness", "weakness", "weight loss"],
        "description": "Requires urgent investigation for GI bleeding.",
    },

    # ── Musculoskeletal ──────────────────────────────────────────────────
    "back pain": {
        "base_severity": 0.30,
        "priority_hint": "GREEN",
        "specialization": "Orthopedics",
        "escalation_factors": ["numbness", "weakness", "loss of bladder control"],
        "description": "Usually mechanical, monitor for red flags.",
    },
    "joint pain": {
        "base_severity": 0.30,
        "priority_hint": "GREEN",
        "specialization": "Orthopedics",
        "escalation_factors": ["swelling", "redness", "fever", "inability to move"],
        "description": "May indicate arthritis or injury.",
    },
    "fracture": {
        "base_severity": 0.65,
        "priority_hint": "ORANGE",
        "specialization": "Orthopedics",
        "escalation_factors": ["open wound", "deformity", "loss of sensation"],
        "description": "Broken bone requiring imaging and treatment.",
    },
    "swelling": {
        "base_severity": 0.35,
        "priority_hint": "GREEN",
        "specialization": "General Medicine",
        "escalation_factors": ["redness", "warmth", "fever", "pain"],
        "description": "May indicate injury, infection, or inflammation.",
    },

    # ── General / Systemic ───────────────────────────────────────────────
    "fever": {
        "base_severity": 0.40,
        "priority_hint": "YELLOW",
        "specialization": "General Medicine",
        "escalation_factors": ["rash", "stiff neck", "confusion", "difficulty breathing"],
        "description": "Indicates infection or inflammatory process.",
    },
    "high fever": {
        "base_severity": 0.60,
        "priority_hint": "ORANGE",
        "specialization": "General Medicine",
        "escalation_factors": ["rash", "stiff neck", "confusion", "seizure"],
        "description": "Temperature > 103°F, requires prompt attention.",
    },
    "fatigue": {
        "base_severity": 0.20,
        "priority_hint": "BLUE",
        "specialization": "General Medicine",
        "escalation_factors": ["weight loss", "fever", "night sweats"],
        "description": "Persistent tiredness, may need blood work.",
    },
    "rash": {
        "base_severity": 0.30,
        "priority_hint": "GREEN",
        "specialization": "Dermatology",
        "escalation_factors": ["fever", "spreading rapidly", "blistering", "breathing difficulty"],
        "description": "Skin reaction, many possible causes.",
    },
    "allergic reaction": {
        "base_severity": 0.65,
        "priority_hint": "ORANGE",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["swelling of throat", "difficulty breathing", "drop in blood pressure"],
        "description": "May progress to anaphylaxis.",
    },
    "bleeding": {
        "base_severity": 0.60,
        "priority_hint": "ORANGE",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["uncontrollable", "dizziness", "weakness", "large wound"],
        "description": "Active hemorrhage requiring assessment.",
    },
    "loss of consciousness": {
        "base_severity": 0.90,
        "priority_hint": "RED",
        "specialization": "Emergency Medicine",
        "escalation_factors": ["head injury", "seizure", "chest pain"],
        "description": "Requires immediate emergency assessment.",
    },
    "fainting": {
        "base_severity": 0.60,
        "priority_hint": "ORANGE",
        "specialization": "General Medicine",
        "escalation_factors": ["chest pain", "irregular heartbeat", "seizure"],
        "description": "Syncope episode, rule out cardiac causes.",
    },

    # ── Pediatric Specific ───────────────────────────────────────────────
    "crying inconsolably": {
        "base_severity": 0.55,
        "priority_hint": "YELLOW",
        "specialization": "Pediatrics",
        "escalation_factors": ["fever", "rash", "vomiting", "lethargy"],
        "description": "In infants, may indicate pain or serious illness.",
    },
    "not feeding": {
        "base_severity": 0.50,
        "priority_hint": "YELLOW",
        "specialization": "Pediatrics",
        "escalation_factors": ["fever", "lethargy", "dehydration"],
        "description": "Refusal to feed in infants may signal illness.",
    },

    # ── ENT ──────────────────────────────────────────────────────────────
    "sore throat": {
        "base_severity": 0.20,
        "priority_hint": "GREEN",
        "specialization": "ENT",
        "escalation_factors": ["fever", "difficulty swallowing", "swollen neck"],
        "description": "Usually viral, may need strep test.",
    },
    "ear pain": {
        "base_severity": 0.25,
        "priority_hint": "GREEN",
        "specialization": "ENT",
        "escalation_factors": ["fever", "discharge", "hearing loss"],
        "description": "May indicate infection.",
    },
    "difficulty swallowing": {
        "base_severity": 0.50,
        "priority_hint": "YELLOW",
        "specialization": "ENT",
        "escalation_factors": ["drooling", "breathing difficulty", "weight loss"],
        "description": "Dysphagia requires evaluation.",
    },
}

# ─── Red-Flag Symptom Combinations ───────────────────────────────────────────
# If ANY of these combinations appear together, immediately escalate to RED.

RED_FLAG_COMBINATIONS = [
    {"symptoms": {"chest pain", "shortness of breath"}, "reason": "Possible MI or PE"},
    {"symptoms": {"severe headache", "stiff neck", "fever"}, "reason": "Possible meningitis"},
    {"symptoms": {"numbness", "slurred speech"}, "reason": "Possible stroke (FAST)"},
    {"symptoms": {"numbness", "facial drooping"}, "reason": "Possible stroke (FAST)"},
    {"symptoms": {"difficulty breathing", "swelling of throat"}, "reason": "Possible anaphylaxis"},
    {"symptoms": {"confusion", "fever", "stiff neck"}, "reason": "Possible meningitis"},
    {"symptoms": {"seizure", "fever"}, "reason": "Febrile seizure, needs emergency care"},
    {"symptoms": {"vomiting blood", "dizziness"}, "reason": "Possible GI hemorrhage"},
    {"symptoms": {"bleeding", "loss of consciousness"}, "reason": "Hemorrhagic shock risk"},
    {"symptoms": {"high fever", "rash", "confusion"}, "reason": "Possible sepsis or meningitis"},
]

# ─── Age-Based Severity Modifiers ────────────────────────────────────────────
# Adjusts the base severity score based on patient age.

AGE_SEVERITY_MODIFIERS = {
    "infant": {"range": (0, 1), "modifier": 1.4, "note": "Infants are high-risk."},
    "toddler": {"range": (1, 5), "modifier": 1.25, "note": "Young children escalate faster."},
    "child": {"range": (5, 12), "modifier": 1.1, "note": "Children need close monitoring."},
    "teen": {"range": (12, 18), "modifier": 1.0, "note": "Standard assessment."},
    "adult": {"range": (18, 60), "modifier": 1.0, "note": "Standard assessment."},
    "senior": {"range": (60, 75), "modifier": 1.2, "note": "Elderly patients are higher risk."},
    "elderly": {"range": (75, 150), "modifier": 1.35, "note": "Very elderly are high-risk."},
}

# ─── Duration-Based Severity Modifiers ───────────────────────────────────────
# Longer symptom durations may indicate chronic issues (lower urgency)
# or worsening conditions (higher urgency for acute symptoms).

DURATION_MODIFIERS = {
    "minutes": 1.3,   # Very acute onset → higher urgency
    "hours": 1.15,    # Acute onset
    "days": 1.0,      # Standard
    "weeks": 0.9,     # Sub-acute, potentially chronic
    "months": 0.85,   # Chronic, less emergent (but needs follow-up)
}

# ─── Priority Thresholds ─────────────────────────────────────────────────────
# Final severity score is mapped to a priority tier.

SEVERITY_THRESHOLDS = {
    "RED": 0.80,      # score >= 0.80
    "ORANGE": 0.60,   # 0.60 <= score < 0.80
    "YELLOW": 0.40,   # 0.40 <= score < 0.60
    "GREEN": 0.20,    # 0.20 <= score < 0.40
    "BLUE": 0.0,      # score < 0.20
}


def get_age_modifier(age: int) -> tuple:
    """
    Get the severity modifier and category for a given age.

    Args:
        age: Patient's age in years.

    Returns:
        Tuple of (modifier_value, category_name, note).
    """
    for category, info in AGE_SEVERITY_MODIFIERS.items():
        low, high = info["range"]
        if low <= age < high:
            return info["modifier"], category, info["note"]
    return 1.0, "adult", "Default assessment."


def get_duration_modifier(duration_unit: str) -> float:
    """
    Get the severity modifier for a symptom duration unit.

    Args:
        duration_unit: Time unit string (minutes, hours, days, weeks, months).

    Returns:
        Modifier float value.
    """
    unit = duration_unit.lower().strip()
    if unit in DURATION_MODIFIERS:
        return DURATION_MODIFIERS[unit]
    plural = unit + "s"
    if plural in DURATION_MODIFIERS:
        return DURATION_MODIFIERS[plural]
    singular = unit.rstrip("s")
    if singular in DURATION_MODIFIERS:
        return DURATION_MODIFIERS[singular]
    return 1.0
