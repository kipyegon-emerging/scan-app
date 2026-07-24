"""Deterministic, form-schema-aware normalisation and validation."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def _empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip().lower() in {"", "null", "none", "unknown"})


def _option_key(value: str, options: dict[str, str]) -> str | None:
    needle = value.strip().casefold()
    for key, label in options.items():
        if needle in {key.casefold(), str(label).casefold()}:
            return key
    return None


def normalize_and_validate(field: dict, value: Any) -> tuple[Any, list[str]]:
    """Return a Kobo-safe value and objective validation findings.

    Empty optional values are preserved as ``None``. Configs may add ``required``,
    ``min`` and ``max`` without changing the existing format.
    """
    findings: list[str] = []
    if _empty(value):
        if field.get("required"):
            findings.append("required field is empty")
        return None, findings

    kind = field.get("type", "text")
    text = str(value).strip()
    if kind in {"integer", "decimal"}:
        candidate = re.sub(r"[^0-9.\-]", "", text.replace(",", ""))
        if candidate.count(".") > 1 or not re.fullmatch(r"-?\d+(?:\.\d+)?", candidate):
            return value, ["not a valid number"]
        if kind == "integer" and "." in candidate:
            return value, ["not a valid integer"]
        number = int(candidate) if kind == "integer" else float(candidate)
        if "min" in field and number < field["min"]:
            findings.append(f"below configured minimum ({field['min']})")
        if "max" in field and number > field["max"]:
            findings.append(f"above configured maximum ({field['max']})")
        return str(number), findings

    if kind == "date":
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).date().isoformat(), findings
            except ValueError:
                pass
        return value, ["not a valid date"]

    options = field.get("options", {})
    if kind == "select_one":
        selected = _option_key(text, options)
        return (selected, findings) if selected else (value, ["not an allowed option"])

    if kind == "select_multiple":
        candidates = value if isinstance(value, list) else re.split(r"[\s,;]+", text)
        selected, invalid = [], []
        for candidate in candidates:
            if not str(candidate).strip():
                continue
            key = _option_key(str(candidate), options)
            if key and key not in selected:
                selected.append(key)
            elif not key:
                invalid.append(str(candidate))
        if invalid:
            findings.append("contains invalid option(s): " + ", ".join(invalid[:3]))
        return " ".join(selected) if selected else None, findings

    if kind == "phone":
        digits = re.sub(r"\D", "", text)
        if len(digits) < 7 or len(digits) > 15:
            findings.append("phone number must contain 7-15 digits")
        return digits, findings
    if kind == "email" and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text):
        findings.append("not a valid email address")
    return text, findings


def validate_submission(fields: dict[str, Any], form_config: dict) -> tuple[dict, dict[str, list[str]]]:
    schema = {field["kobo_name"]: field for field in form_config["fields"]}
    unknown = set(fields) - set(schema)
    errors: dict[str, list[str]] = {name: ["field is not configured for this form"] for name in unknown}
    clean: dict[str, Any] = {}
    for name, field in schema.items():
        value, findings = normalize_and_validate(field, fields.get(name))
        if value is not None:
            clean[name] = value
        if findings:
            errors[name] = findings
    return clean, errors


def score_field(value: Any, ai_confidence: Any, validation_errors: list[str], image_quality: int | None) -> tuple[int, str, bool, str]:
    score = 85 if str(ai_confidence).lower() in {"high", "90", "95", "100"} else 62
    if value is None:
        score -= 35
    if validation_errors:
        score -= 45
    if image_quality is not None:
        score += max(-20, min(10, image_quality - 80)) // 2
    score = max(0, min(100, score))
    level = "high" if score >= 90 else "medium" if score >= 70 else "low"
    reason = "; ".join(validation_errors) if validation_errors else ("missing or unreadable value" if value is None else "AI signal adjusted using image quality and schema validation")
    return score, level, score < 90 or bool(validation_errors), reason
