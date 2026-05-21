from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


EXPORT_COLUMNS = [
    "publication_date",
    "application_deadline",
    "auction_date",
    "station_match",
    "area_m2",
    "area_sotka",
    "title",
    "purpose",
    "contract_type",
    "price_text",
    "source",
    "status",
    "is_interesting",
    "is_notified",
    "url",
]


def export_items(items: list[dict[str, Any]], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(items)
    if not frame.empty:
        columns = [column for column in EXPORT_COLUMNS if column in frame.columns]
        frame = frame[columns]
    if output.suffix.lower() == ".csv":
        frame.to_csv(output, index=False)
    else:
        frame.to_excel(output, index=False)
    return output
