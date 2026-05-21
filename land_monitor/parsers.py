from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

import pandas as pd


AREA_PATTERNS = [
    re.compile(r"(?:площад(?:ь|ью)\s*[:\-]?\s*)?(\d[\d\s]*(?:[,.]\d+)?)\s*(?:кв\.?\s*м|м²|м2)", re.IGNORECASE),
    re.compile(r"площад(?:ь|ью)\s*[:\-]?\s*(\d[\d\s]*(?:[,.]\d+)?)(?!\s*(?:га|сот))", re.IGNORECASE),
]
HECTARE_PATTERN = re.compile(r"(\d[\d\s]*(?:[,.]\d+)?)\s*га\b", re.IGNORECASE)
SOTKA_PATTERN = re.compile(r"(\d[\d\s]*(?:[,.]\d+)?)\s*сот(?:ка|ки|ок)?\b", re.IGNORECASE)


def normalize_number(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def parse_area_m2(text: str | None) -> float | None:
    if not text:
        return None
    hectare = HECTARE_PATTERN.search(text)
    if hectare:
        return normalize_number(hectare.group(1)) * 10000
    sotka = SOTKA_PATTERN.search(text)
    if sotka:
        return normalize_number(sotka.group(1)) * 100
    for pattern in AREA_PATTERNS:
        match = pattern.search(text)
        if match:
            return normalize_number(match.group(1))
    return None


def parse_date_value(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    parsed = pd.to_datetime(str(value), dayfirst=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def detect_purpose(text: str | None) -> str | None:
    normalized = (text or "").lower()
    if "ижс" in normalized or "индивидуального жилищного строительства" in normalized:
        return "ИЖС"
    if "лпх" in normalized or "личного подсобного хозяйства" in normalized:
        return "ЛПХ"
    if "садовод" in normalized:
        return "садоводство"
    return None


def detect_contract_type(text: str | None) -> str | None:
    normalized = (text or "").lower()
    if "аренд" in normalized:
        return "аренда"
    if "продаж" in normalized or "собственность" in normalized:
        return "продажа"
    return None


def first_present(row: dict[str, Any], names: list[str]) -> Any:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name.lower())
        if value is not None and not pd.isna(value) and str(value).strip():
            return value
    return None


def stringify(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def content_hash(item: dict[str, Any]) -> str:
    parts = [
        stringify(item.get("source")),
        stringify(item.get("external_id")),
        stringify(item.get("url")),
        stringify(item.get("title")),
        stringify(item.get("raw_text")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(stringify(item.get(key)) for key in ("title", "description", "location", "raw_text"))
    area_m2 = item.get("area_m2")
    if area_m2 in (None, ""):
        area_m2 = parse_area_m2(text)
    elif not isinstance(area_m2, (int, float)):
        area_m2 = parse_area_m2(str(area_m2)) or normalize_number(str(area_m2))

    normalized = {
        "source": stringify(item.get("source")) or "unknown",
        "external_id": stringify(item.get("external_id")),
        "title": stringify(item.get("title")) or "Без названия",
        "description": stringify(item.get("description")),
        "location": stringify(item.get("location")),
        "station_match": stringify(item.get("station_match")),
        "area_m2": area_m2,
        "area_sotka": round(area_m2 / 100, 2) if area_m2 else None,
        "purpose": stringify(item.get("purpose")) or detect_purpose(text),
        "contract_type": stringify(item.get("contract_type")) or detect_contract_type(text),
        "price_text": stringify(item.get("price_text")),
        "status": stringify(item.get("status")) or "new",
        "publication_date": parse_date_value(item.get("publication_date")),
        "application_deadline": parse_date_value(item.get("application_deadline")),
        "auction_date": parse_date_value(item.get("auction_date")),
        "url": stringify(item.get("url")),
        "raw_text": stringify(item.get("raw_text")) or text,
        "is_interesting": bool(item.get("is_interesting", False)),
        "is_notified": bool(item.get("is_notified", False)),
    }
    normalized["content_hash"] = stringify(item.get("content_hash")) or content_hash(normalized)
    return normalized
