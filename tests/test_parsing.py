from land_monitor.parsers import detect_contract_type, detect_purpose, parse_area_m2, parse_date_value


def test_parse_area_m2_common_formats():
    assert parse_area_m2("земельный участок площадью 1447 кв. м") == 1447.0
    assert parse_area_m2("участок 1447 м² для ИЖС") == 1447.0
    assert parse_area_m2("площадь: 1447") == 1447.0
    assert parse_area_m2("1 447,5 кв.м") == 1447.5


def test_parse_area_m2_converts_hectares_and_sotka():
    assert parse_area_m2("площадь 0,15 га") == 1500.0
    assert parse_area_m2("15 соток") == 1500.0


def test_parse_area_m2_returns_none_for_unknown_text():
    assert parse_area_m2("право заключения договора аренды") is None


def test_detect_purpose_and_contract_type():
    text = "Аукцион на право заключения договора аренды участка для индивидуального жилищного строительства"

    assert detect_purpose(text) == "ИЖС"
    assert detect_contract_type(text) == "аренда"


def test_parse_date_value_accepts_russian_date_string():
    assert parse_date_value("21.05.2026") == "2026-05-21"
