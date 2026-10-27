"""Input validation and demo-mode privacy guardrails."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


class ValidationError(ValueError):
    pass


def _require_string(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value.strip()


def _require_list(data: dict, key: str, minimum: int = 1) -> list:
    value = data.get(key)
    if not isinstance(value, list) or len(value) < minimum:
        raise ValidationError(f"{key} must contain at least {minimum} item(s)")
    return value


def validate_public_url(value: str, *, demo_mode: bool) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValidationError("public_url must be an absolute https URL")
    if demo_mode and not (
        parsed.hostname == "example.com" or (parsed.hostname or "").endswith(".example.com")
    ):
        raise ValidationError("demo mode only permits reserved example.com URLs")


def validate_business(data: dict, *, demo_mode: bool = False) -> dict:
    for key in ("name", "category", "town", "address", "phone", "tagline", "description"):
        _require_string(data, key)
    validate_public_url(_require_string(data, "public_url"), demo_mode=demo_mode)

    digits = re.sub(r"\D", "", data["phone"])
    if len(digits) not in {10, 11}:
        raise ValidationError("phone must contain 10 digits, or 11 digits starting with 1")
    if demo_mode and "555" not in digits:
        raise ValidationError("demo fixtures must use a reserved 555 phone number")

    rating = data.get("rating")
    if not isinstance(rating, (int, float)) or not 0 <= float(rating) <= 5:
        raise ValidationError("rating must be a number from 0 to 5")
    if not isinstance(data.get("review_count"), int) or data["review_count"] < 0:
        raise ValidationError("review_count must be a non-negative integer")

    for item in _require_list(data, "hours", 1):
        if not isinstance(item, dict):
            raise ValidationError("each hours item must be an object")
        _require_string(item, "day")
        _require_string(item, "hours")
    for item in _require_list(data, "services", 3):
        if not isinstance(item, dict):
            raise ValidationError("each service must be an object")
        _require_string(item, "name")
        _require_string(item, "description")
    for item in _require_list(data, "reviews", 2):
        if not isinstance(item, dict):
            raise ValidationError("each review must be an object")
        _require_string(item, "author")
        _require_string(item, "quote")
    for item in _require_list(data, "photos", 3):
        if not isinstance(item, dict):
            raise ValidationError("each photo must be an object")
        _require_string(item, "label")
        _require_string(item, "alt")
        if item.get("path"):
            _require_string(item, "path")
            if demo_mode:
                raise ValidationError("demo mode only permits generated placeholder photos")
        else:
            _require_string(item, "color_start")
            _require_string(item, "color_end")

    if demo_mode and data.get("fixture_type") != "fictional":
        raise ValidationError("demo mode requires fixture_type to be fictional")
    return data


def validate_prospect(data: dict, *, demo_mode: bool = False) -> dict:
    for key in (
        "first_name",
        "last_name",
        "company_name",
        "role",
        "headline",
        "subhead",
        "context",
        "recommendation_title",
        "recommendation_body",
        "cta_label",
        "cta_url",
    ):
        _require_string(data, key)
    validate_public_url(data["cta_url"], demo_mode=demo_mode)
    for item in _require_list(data, "observations", 3):
        if not isinstance(item, dict):
            raise ValidationError("each observation must be an object")
        _require_string(item, "title")
        _require_string(item, "detail")
    if demo_mode and data.get("fixture_type") != "fictional":
        raise ValidationError("demo mode requires fixture_type to be fictional")
    return data


def require_existing_json(path: Path) -> None:
    if not path.is_file() or path.suffix.lower() != ".json":
        raise ValidationError(f"expected a JSON file: {path}")
