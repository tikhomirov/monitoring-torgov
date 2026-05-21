from land_monitor.filters import find_station, is_relevant


CONFIG = {
    "filters": {
        "min_area_m2": 1000,
        "stations": ["Каннельярви", "Кирилловское", "Рощино"],
        "positive_keywords": ["земельный участок", "ИЖС", "ЛПХ", "садоводство", "39.18"],
        "strong_keywords": ["ИЖС", "ЛПХ", "садоводство", "39.18"],
        "negative_keywords": ["нежилое здание", "помещение", "гараж"],
    }
}


def test_find_station_is_case_insensitive():
    assert find_station("участок рядом со станцией каннельярви", CONFIG) == "Каннельярви"


def test_is_relevant_accepts_matching_station_area_and_keywords():
    item = {
        "title": "Земельный участок Каннельярви",
        "description": "ИЖС, аренда, ст. 39.18",
        "location": "Каннельярви",
        "area_m2": 1447,
    }

    relevant, reasons = is_relevant(item, CONFIG)

    assert relevant is True
    assert "station:Каннельярви" in reasons
    assert "area_ok" in reasons
    assert "positive_keywords" in reasons


def test_is_relevant_rejects_negative_keywords():
    item = {
        "title": "Гараж рядом с Рощино",
        "description": "земельный участок",
        "location": "Рощино",
        "area_m2": 2000,
    }

    relevant, reasons = is_relevant(item, CONFIG)

    assert relevant is False
    assert "negative_keywords" in reasons


def test_is_relevant_accepts_unknown_area_with_station_and_strong_keyword():
    item = {
        "title": "Извещение 39.18 Каннельярви",
        "description": "земельный участок для ИЖС",
        "location": "Каннельярви",
        "area_m2": None,
    }

    relevant, reasons = is_relevant(item, CONFIG)

    assert relevant is True
    assert "area_unknown" in reasons


def test_is_relevant_rejects_small_area():
    item = {
        "title": "Земельный участок Каннельярви",
        "description": "ИЖС",
        "location": "Каннельярви",
        "area_m2": 600,
    }

    relevant, reasons = is_relevant(item, CONFIG)

    assert relevant is False
    assert "area_too_small" in reasons
