from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


DEFAULT_CONFIG: dict[str, Any] = {
    "database": {"path": "data/land_monitor.sqlite3"},
    "exports": {"path": "data/land_items.xlsx"},
    "http": {"timeout_seconds": 30, "user_agent": "LandMonitor/0.1"},
    "sources": {
        "gis_torgi": {"enabled": True, "excel_url": ""},
        "vbglenobl": {"enabled": True, "list_url": ""},
    },
    "filters": {
        "min_area_m2": 1000,
        "stations": [
            "Каннельярви",
            "Кирилловское",
            "Гаврилово",
            "Рощино",
            "Победа",
            "Горьковское",
            "Приветнинское",
            "Ландышевка",
            "Межозерное",
        ],
        "positive_keywords": [
            "земельный участок",
            "индивидуального жилищного строительства",
            "ИЖС",
            "личного подсобного хозяйства",
            "ЛПХ",
            "садоводство",
            "договор аренды",
            "право заключения договора аренды",
            "намерении участвовать",
            "ст. 39.18",
            "39.18",
            "аукцион",
        ],
        "strong_keywords": ["ИЖС", "ЛПХ", "садоводство", "ст. 39.18", "39.18"],
        "negative_keywords": [
            "нежилое здание",
            "помещение",
            "гараж",
            "коммерческое",
            "сельскохозяйственное производство",
            "земельные участки общего назначения",
        ],
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    load_dotenv()
    config_path = Path(path)
    data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Config file {config_path} must contain a YAML mapping")
            data = loaded

    config = deep_merge(DEFAULT_CONFIG, data)
    gis_url = os.getenv("GIS_TORGI_EXCEL_URL")
    if gis_url:
        config["sources"]["gis_torgi"]["excel_url"] = gis_url

    vbg_url = os.getenv("VBGLENOBL_LIST_URL")
    if vbg_url:
        config["sources"]["vbglenobl"]["list_url"] = vbg_url

    db_path = os.getenv("LAND_MONITOR_DB")
    if db_path:
        config["database"]["path"] = db_path

    return config
