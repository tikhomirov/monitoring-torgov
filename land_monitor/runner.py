from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from land_monitor.filters import find_station, is_relevant
from land_monitor.notifier import TelegramNotifier
from land_monitor.parsers import normalize_item
from land_monitor.sources import build_sources
from land_monitor.storage import LandStore


LOGGER = logging.getLogger(__name__)


@dataclass
class RunResult:
    fetched: int = 0
    inserted: int = 0
    relevant: int = 0
    notified: int = 0
    errors: int = 0


def run_once(
    config: dict[str, Any],
    store: LandStore | None = None,
    sources: list[Any] | None = None,
    notifier: TelegramNotifier | None = None,
    selected_source: str | None = None,
    dry_run: bool = False,
) -> RunResult:
    store = store or LandStore(config["database"]["path"])
    sources = sources if sources is not None else build_sources(config, selected_source)
    notifier = notifier or TelegramNotifier()
    result = RunResult()

    if not dry_run:
        store.initialize()

    for source in sources:
        try:
            items = source.fetch_items()
        except Exception as error:
            LOGGER.error("Source %s failed: %s", getattr(source, "name", source.__class__.__name__), error)
            result.errors += 1
            continue

        result.fetched += len(items)
        for raw_item in items:
            item = normalize_item(raw_item)
            station = item.get("station_match") or find_station("\n".join(str(item.get(key) or "") for key in ("title", "description", "location", "raw_text")), config)
            item["station_match"] = station or ""
            relevant, reasons = is_relevant(item, config)
            item["is_interesting"] = relevant
            if reasons:
                item["raw_text"] = f"{item.get('raw_text') or ''}\n\nrelevance_reasons: {', '.join(reasons)}".strip()
            if relevant:
                result.relevant += 1

            if dry_run:
                LOGGER.info("DRY RUN: %s relevant=%s reasons=%s", item["title"], relevant, reasons)
                continue

            item_id = store.insert_item(item)
            if item_id is None:
                continue
            result.inserted += 1
            if relevant and notifier.is_configured() and notifier.send_item(item):
                store.mark_notified(item_id)
                result.notified += 1

    LOGGER.info(
        "Run finished: fetched=%s inserted=%s relevant=%s notified=%s errors=%s",
        result.fetched,
        result.inserted,
        result.relevant,
        result.notified,
        result.errors,
    )
    return result
