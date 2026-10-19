"""
NLP parser utilities for the Intake Agent.

Provides regex-based extraction of structured patient data from
free-text or conversational input. No heavy NLP library is required;
patterns are designed to capture common ways users describe symptoms.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from data.medical_guidelines import SYMPTOM_GUIDELINES


# ─── Precompiled Patterns ─────────────────────────────────────────────────────

# Age extraction: "I am 45", "age 45", "45 years old", "45 y/o", "my son is 3"
AGE_PATTERNS = [
    re.compile(r"\b(?:i am|i'm|age|aged)\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,3})[\s-]*(?:years?[\s-]*old|y/?o|yrs?)\b", re.IGNORECASE),
    re.compile(r"\b(?:my\s+(?:son|daughter|child|mother|father|wife|husband)\s+is)\s+(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\bpatient\s+(?:is\s+)?(\d{1,3})\b", re.IGNORECASE),
]

# Duration extraction: "for 3 days", "since 2 hours", "lasting 1 week"
DURATION_PATTERNS = [
    re.compile(
        r"\b(?:for|since|lasting|past|last)\s+(\d+)\s*(minutes?|hours?|days?|weeks?|months?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d+)\s*(minutes?|hours?|days?|weeks?|months?)\s+(?:ago|now|long)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:started|began|onset)\s+(\d+)\s*(minutes?|hours?|days?|weeks?|months?)\s*(?:ago|back)?\b",
        re.IGNORECASE,
    ),
]

# Name extraction: "my name is John", "I'm Jane Doe", "patient name: ..."
NAME_PATTERNS = [
    re.compile(
        r"(?:my name is|i'm|i am|name:\s*|patient(?:\s+name)?:\s*)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        re.IGNORECASE,
    ),
]

# Gender extraction
GENDER_PATTERNS = [
    re.compile(r"\b(male|female|man|woman|boy|girl)\b", re.IGNORECASE),
]

# Contact extraction (phone or email)
CONTACT_PATTERNS = [
    re.compile(r"\b(\d{10})\b"),
    re.compile(r"\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b"),
    re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"),
]

# Build a sorted symptom list (longest first for greedy matching)
_KNOWN_SYMPTOMS = sorted(SYMPTOM_GUIDELINES.keys(), key=len, reverse=True)


def extract_age(text: str) -> Optional[int]:
    """
    Extract patient age from free text.

    Args:
        text: Raw user input string.

    Returns:
        Extracted age as integer, or None if not found.
    """
    for pattern in AGE_PATTERNS:
        match = pattern.search(text)
        if match:
            age = int(match.group(1))
            if 0 <= age <= 150:
                return age
    return None


def extract_symptoms(text: str) -> List[str]:
    """
    Extract known symptoms from free text by matching against
    the medical guidelines symptom database.

    Uses longest-match-first strategy to avoid partial matches
    (e.g., "chest pain" should match before "chest").

    Args:
        text: Raw user input string.

    Returns:
        List of matched symptom strings (deduplicated).
    """
    text_lower = text.lower()
    found = []
    matched_spans = []  # Track matched positions to avoid overlaps

    for symptom in _KNOWN_SYMPTOMS:
        # Use word boundary matching
        pattern = re.compile(r"\b" + re.escape(symptom) + r"\b", re.IGNORECASE)
        for match in pattern.finditer(text_lower):
            start, end = match.span()
            # Check this span doesn't overlap with an already matched span
            overlap = any(
                not (end <= ms or start >= me)
                for ms, me in matched_spans
            )
            if not overlap and symptom not in found:
                found.append(symptom)
                matched_spans.append((start, end))

    return found


def extract_duration(text: str) -> Optional[str]:
    """
    Extract symptom duration from free text.

    Args:
        text: Raw user input string.

    Returns:
        Duration string (e.g., "3 days"), or None if not found.
    """
    for pattern in DURATION_PATTERNS:
        match = pattern.search(text)
        if match:
            number = match.group(1)
            unit = match.group(2).lower()
            # Normalize to plural
            if not unit.endswith("s") and int(number) != 1:
                unit += "s"
            return f"{number} {unit}"
    return None


def extract_name(text: str) -> Optional[str]:
    """
    Extract patient name from free text.

    Args:
        text: Raw user input string.

    Returns:
        Extracted name string, or None if not found.
    """
    for pattern in NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            name = match.group(1).strip()
            # Filter out symptom words mistakenly captured as names
            if name.lower() not in SYMPTOM_GUIDELINES and len(name) >= 2:
                return name.title()
    return None


def extract_gender(text: str) -> str:
    """
    Extract gender from free text.

    Args:
        text: Raw user input string.

    Returns:
        Gender string ("Male", "Female", or "Unknown").
    """
    for pattern in GENDER_PATTERNS:
        match = pattern.search(text)
        if match:
            word = match.group(1).lower()
            if word in ("male", "man", "boy"):
                return "Male"
            elif word in ("female", "woman", "girl"):
                return "Female"
    return "Unknown"


def extract_contact(text: str) -> Optional[str]:
    """
    Extract a phone number or email from free text.

    Args:
        text: Raw user input string.

    Returns:
        Contact string, or None if not found.
    """
    for pattern in CONTACT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def parse_patient_input(text: str) -> Dict:
    """
    Parse free-text patient input and extract all available structured fields.

    This is the main entry point used by the Intake Agent.

    Args:
        text: Raw user input describing the patient and symptoms.

    Returns:
        Dictionary with extracted fields:
        - name (str or None)
        - age (int or None)
        - gender (str)
        - symptoms (list[str])
        - symptom_duration (str or None)
        - contact (str or None)
        - raw_input (str)
        - extraction_confidence (float 0-1)
        - missing_fields (list[str])
    """
    name = extract_name(text)
    age = extract_age(text)
    symptoms = extract_symptoms(text)
    duration = extract_duration(text)
    gender = extract_gender(text)
    contact = extract_contact(text)

    # Calculate extraction confidence
    total_fields = 5  # name, age, symptoms, duration, contact
    filled_fields = sum([
        name is not None,
        age is not None,
        len(symptoms) > 0,
        duration is not None,
        contact is not None,
    ])
    confidence = filled_fields / total_fields

    # Track missing fields
    missing = []
    if name is None:
        missing.append("name")
    if age is None:
        missing.append("age")
    if not symptoms:
        missing.append("symptoms")
    if duration is None:
        missing.append("symptom_duration")

    return {
        "name": name,
        "age": age,
        "gender": gender,
        "symptoms": symptoms,
        "symptom_duration": duration,
        "contact": contact,
        "raw_input": text,
        "extraction_confidence": round(confidence, 2),
        "missing_fields": missing,
    }
