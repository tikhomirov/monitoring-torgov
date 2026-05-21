from __future__ import annotations

import argparse
import logging
import sys

from land_monitor.config import load_config
from land_monitor.exporter import export_items
from land_monitor.runner import run_once
from land_monitor.storage import LandStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Land Monitor: поиск земельных лотов")
    parser.add_argument("--config", default="config.yaml", help="Путь к config.yaml")
    parser.add_argument("--once", action="store_true", help="Выполнить одну проверку и завершиться")
    parser.add_argument("--source", choices=["gis_torgi", "vbglenobl"], help="Запустить только один источник")
    parser.add_argument("--dry-run", action="store_true", help="Показать найденные записи без сохранения в SQLite")
    parser.add_argument("--export", nargs="?", const=True, help="Экспортировать записи в Excel/CSV после проверки")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    store = LandStore(config["database"]["path"])

    run_once(config, store=store, selected_source=args.source, dry_run=args.dry_run)

    if args.export:
        export_path = config.get("exports", {}).get("path", "data/land_items.xlsx") if args.export is True else str(args.export)
        output = export_items(store.list_items(), export_path)
        logging.info("Exported items to %s", output)

    if not args.once:
        logging.info("One-shot run completed. Use cron or systemd timer for periodic execution.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
