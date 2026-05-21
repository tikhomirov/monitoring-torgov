from land_monitor.runner import run_once
from land_monitor.storage import LandStore


CONFIG = {
    "database": {"path": "unused.db"},
    "sources": {
        "gis_torgi": {"enabled": False},
        "vbglenobl": {"enabled": False},
    },
    "filters": {
        "min_area_m2": 1000,
        "stations": ["Каннельярви"],
        "positive_keywords": ["земельный участок", "ИЖС", "39.18"],
        "strong_keywords": ["ИЖС", "39.18"],
        "negative_keywords": ["гараж"],
    },
}


class FakeSource:
    name = "fake"

    def fetch_items(self):
        return [
            {
                "source": "fake",
                "external_id": "42",
                "title": "Земельный участок Каннельярви",
                "description": "ИЖС, аренда, ст. 39.18",
                "location": "Каннельярви",
                "area_m2": 1447,
                "url": "https://example.test/42",
                "raw_text": "raw text",
            }
        ]


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def is_configured(self):
        return True

    def send_item(self, item):
        self.sent.append(item)
        return True


def test_run_once_inserts_relevant_items_and_marks_notified(tmp_path):
    store = LandStore(tmp_path / "land.db")
    notifier = FakeNotifier()

    result = run_once(CONFIG, store=store, sources=[FakeSource()], notifier=notifier, dry_run=False)

    assert result.fetched == 1
    assert result.inserted == 1
    assert result.relevant == 1
    assert result.notified == 1
    assert store.count_items() == 1
    assert store.list_items()[0]["is_notified"] == 1
    assert notifier.sent[0]["station_match"] == "Каннельярви"


def test_run_once_dry_run_does_not_write(tmp_path):
    store = LandStore(tmp_path / "land.db")

    result = run_once(CONFIG, store=store, sources=[FakeSource()], notifier=FakeNotifier(), dry_run=True)

    assert result.fetched == 1
    assert result.inserted == 0
    assert store.count_items() == 0
