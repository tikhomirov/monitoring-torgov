from land_monitor.storage import LandStore


def sample_item(title="Земельный участок Каннельярви", external_id="1"):
    return {
        "source": "test",
        "external_id": external_id,
        "title": title,
        "description": "ИЖС, аренда, ст. 39.18",
        "location": "Каннельярви",
        "station_match": "Каннельярви",
        "area_m2": 1447,
        "area_sotka": 14.47,
        "purpose": "ИЖС",
        "contract_type": "аренда",
        "price_text": "1000 руб.",
        "status": "new",
        "publication_date": "2026-05-21",
        "application_deadline": "2026-05-30",
        "auction_date": None,
        "url": "https://example.test/1",
        "raw_text": "raw",
        "is_interesting": True,
        "is_notified": False,
    }


def test_database_is_created_and_deduplicates_by_content_hash(tmp_path):
    store = LandStore(tmp_path / "land.db")
    store.initialize()

    first = store.insert_item(sample_item())
    second = store.insert_item(sample_item())

    assert first is not None
    assert second is None
    assert store.count_items() == 1


def test_update_status_persists(tmp_path):
    store = LandStore(tmp_path / "land.db")
    store.initialize()
    item_id = store.insert_item(sample_item())

    store.update_status(item_id, "applied")

    item = store.get_item(item_id)
    assert item["status"] == "applied"
    assert item["updated_at"] is not None


def test_mark_notified_persists(tmp_path):
    store = LandStore(tmp_path / "land.db")
    store.initialize()
    item_id = store.insert_item(sample_item())

    store.mark_notified(item_id)

    assert store.get_item(item_id)["is_notified"] == 1
