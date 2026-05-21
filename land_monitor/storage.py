from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from land_monitor.parsers import content_hash


COLUMNS = [
    "source",
    "external_id",
    "title",
    "description",
    "location",
    "station_match",
    "area_m2",
    "area_sotka",
    "purpose",
    "contract_type",
    "price_text",
    "status",
    "publication_date",
    "application_deadline",
    "auction_date",
    "url",
    "raw_text",
    "content_hash",
    "is_interesting",
    "is_notified",
]


class LandStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS land_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    external_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    location TEXT,
                    station_match TEXT,
                    area_m2 REAL,
                    area_sotka REAL,
                    purpose TEXT,
                    contract_type TEXT,
                    price_text TEXT,
                    status TEXT NOT NULL DEFAULT 'new',
                    publication_date TEXT,
                    application_deadline TEXT,
                    auction_date TEXT,
                    url TEXT,
                    raw_text TEXT,
                    content_hash TEXT NOT NULL UNIQUE,
                    is_interesting INTEGER NOT NULL DEFAULT 0,
                    is_notified INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_land_items_status ON land_items(status)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_land_items_station ON land_items(station_match)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_land_items_deadline ON land_items(application_deadline)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_land_items_interesting ON land_items(is_interesting)")

    def insert_item(self, item: dict[str, Any]) -> int | None:
        self.initialize()
        now = datetime.now().isoformat(timespec="seconds")
        values = {column: item.get(column) for column in COLUMNS}
        values["content_hash"] = values.get("content_hash") or content_hash(item)
        values["is_interesting"] = int(bool(values.get("is_interesting")))
        values["is_notified"] = int(bool(values.get("is_notified")))
        values["created_at"] = now
        values["updated_at"] = now
        columns = COLUMNS + ["created_at", "updated_at"]
        placeholders = ", ".join(f":{column}" for column in columns)
        sql = f"INSERT OR IGNORE INTO land_items ({', '.join(columns)}) VALUES ({placeholders})"
        with self.connect() as connection:
            cursor = connection.execute(sql, values)
            if cursor.rowcount == 0:
                return None
            return int(cursor.lastrowid)

    def list_items(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        self.initialize()
        filters = filters or {}
        where: list[str] = []
        params: dict[str, Any] = {}

        for field in ("station_match", "source", "status"):
            value = filters.get(field)
            if value:
                where.append(f"{field} = :{field}")
                params[field] = value

        if filters.get("min_area_m2"):
            where.append("area_m2 >= :min_area_m2")
            params["min_area_m2"] = float(filters["min_area_m2"])
        if filters.get("only_interesting"):
            where.append("is_interesting = 1")
        if filters.get("only_notified"):
            where.append("is_notified = 1")
        if filters.get("only_new"):
            where.append("status = 'new'")

        sql = "SELECT * FROM land_items"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY is_interesting DESC, COALESCE(application_deadline, publication_date, created_at) DESC, id DESC"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, params).fetchall()]

    def get_item(self, item_id: int) -> dict[str, Any]:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM land_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise KeyError(f"land item {item_id} not found")
            return dict(row)

    def count_items(self) -> int:
        self.initialize()
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM land_items").fetchone()[0])

    def metrics(self) -> dict[str, int]:
        self.initialize()
        today = datetime.now().date()
        seven_days = today + timedelta(days=7)
        with self.connect() as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM land_items").fetchone()[0])
            new = int(connection.execute("SELECT COUNT(*) FROM land_items WHERE status = 'new'").fetchone()[0])
            interesting = int(connection.execute("SELECT COUNT(*) FROM land_items WHERE is_interesting = 1").fetchone()[0])
            upcoming = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM land_items
                    WHERE application_deadline IS NOT NULL
                      AND application_deadline >= ?
                      AND application_deadline <= ?
                    """,
                    (today.isoformat(), seven_days.isoformat()),
                ).fetchone()[0]
            )
        return {"total": total, "new": new, "interesting": interesting, "upcoming_deadlines": upcoming}

    def update_status(self, item_id: int, status: str) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "UPDATE land_items SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(timespec="seconds"), item_id),
            )

    def set_interesting(self, item_id: int, value: bool) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "UPDATE land_items SET is_interesting = ?, updated_at = ? WHERE id = ?",
                (int(value), datetime.now().isoformat(timespec="seconds"), item_id),
            )

    def mark_notified(self, item_id: int) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "UPDATE land_items SET is_notified = 1, updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), item_id),
            )
