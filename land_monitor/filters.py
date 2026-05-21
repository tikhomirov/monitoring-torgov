from __future__ import annotations

from typing import Any


def item_text(item: dict[str, Any]) -> str:
    return "\n".join(str(item.get(key) or "") for key in ("title", "description", "location", "purpose", "contract_type", "raw_text"))


def contains_any(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword.lower() in normalized for keyword in keywords)


def find_station(text: str, config: dict[str, Any]) -> str | None:
    normalized = text.lower()
    for station in config.get("filters", {}).get("stations", []):
        if station.lower() in normalized:
            return station
    return None


def is_relevant(item: dict[str, Any], config: dict[str, Any]) -> tuple[bool, list[str]]:
    filters = config.get("filters", {})
    text = item_text(item)
    reasons: list[str] = []

    station = item.get("station_match") or find_station(text, config)
    if not station:
        return False, ["station_missing"]
    reasons.append(f"station:{station}")

    negative_keywords = filters.get("negative_keywords", [])
    if contains_any(text, negative_keywords):
        return False, reasons + ["negative_keywords"]

    positive_keywords = filters.get("positive_keywords", [])
    has_positive = contains_any(text, positive_keywords)
    if not has_positive:
        return False, reasons + ["positive_keywords_missing"]
    reasons.append("positive_keywords")

    min_area_m2 = float(filters.get("min_area_m2", 1000))
    area_m2 = item.get("area_m2")
    if area_m2 is None:
        strong_keywords = filters.get("strong_keywords", [])
        if contains_any(text, strong_keywords):
            return True, reasons + ["area_unknown"]
        return False, reasons + ["area_unknown_weak_keywords"]

    if float(area_m2) < min_area_m2:
        return False, reasons + ["area_too_small"]

    return True, reasons + ["area_ok"]
