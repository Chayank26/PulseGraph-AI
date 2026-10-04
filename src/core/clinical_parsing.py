"""Strict parsing shared by triage and clinical data request validation."""
import math
import re
from typing import Any, Optional


def parse_boolean(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        return {"true": True, "yes": True, "1": True,
                "false": False, "no": False, "0": False}.get(value.strip().lower())
    return None


def parse_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError, OverflowError):
        return None


def parse_enum_score(value: Any) -> Optional[int]:
    if isinstance(value, str):
        match = re.fullmatch(r"([012])(?:\s+\([^()]+\))?", value.strip())
        return int(match[1]) if match else None
    number = parse_number(value)
    return int(number) if number in (0, 1, 2) else None
