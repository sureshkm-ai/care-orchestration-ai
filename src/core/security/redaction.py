"""PHI redaction engine for logs, traces, exceptions, and metrics.

Ensures no raw PHI appears in any observability surface.
"""

from __future__ import annotations

import re
from typing import Any

# Common PHI patterns to redact
_PHI_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # SSN: xxx-xx-xxxx
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    # MRN: common formats (MRN followed by digits)
    (re.compile(r"\bMRN[-:]?\s*\d{4,}\b", re.IGNORECASE), "[REDACTED-MRN]"),
    # Date of birth patterns (MM/DD/YYYY, YYYY-MM-DD)
    (
        re.compile(r"\b(?:DOB|date.?of.?birth)[\s:]*\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b", re.I),
        "[REDACTED-DOB]",
    ),
    # Phone numbers
    (re.compile(r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED-PHONE]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED-EMAIL]"),
]

# Keys that likely contain PHI (case-insensitive matching)
_SENSITIVE_KEYS = frozenset(
    {
        "patient_name",
        "name",
        "given_name",
        "family_name",
        "ssn",
        "social_security",
        "mrn",
        "medical_record_number",
        "address",
        "street",
        "city",
        "zip",
        "postal_code",
        "phone",
        "telephone",
        "email",
        "contact",
        "dob",
        "date_of_birth",
        "birth_date",
    }
)


def redact_string(text: str) -> str:
    """Apply PHI pattern redaction to a string."""
    result = text
    for pattern, replacement in _PHI_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact_dict(data: dict[str, Any], depth: int = 0) -> dict[str, Any]:
    """Recursively redact PHI from a dictionary (for log event dicts).

    Redacts values whose keys match known sensitive field names,
    and applies pattern-based redaction to string values.
    """
    if depth > 10:
        return data

    result: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if key_lower in _SENSITIVE_KEYS:
            result[key] = "[REDACTED]"
        elif isinstance(value, str):
            result[key] = redact_string(value)
        elif isinstance(value, dict):
            result[key] = redact_dict(value, depth + 1)
        elif isinstance(value, list):
            result[key] = [
                redact_dict(item, depth + 1)
                if isinstance(item, dict)
                else redact_string(item)
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def sanitize_exception(exc: BaseException) -> str:
    """Sanitize an exception message by redacting PHI patterns."""
    return redact_string(str(exc))
