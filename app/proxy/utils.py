#!/usr/bin/env python
from typing import Any


def clean_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    return str(value).strip()
