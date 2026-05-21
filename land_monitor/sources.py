from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from io import BytesIO
from typing import Any
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

from land_monitor.parsers import first_present, normalize_item, stringify


LOGGER = logging.getLogger(__name__)


@dataclass
class HttpSettings:
    timeout_seconds: int = 30
    user_agent: str = "LandMonitor/0.1"

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent}


class GisTorgiSource:
    name = "gis_torgi"

    def __init__(self, excel_url: str, http: HttpSettings):
        self.excel_url = excel_url
        self.http = http

    def fetch_items(self) -> list[dict[str, Any]]:
        if not self.excel_url:
            LOGGER.warning("GIS Torgi source skipped: excel_url is empty")
            return []
        response = requests.get(self.excel_url, headers=self.http.headers, timeout=self.http.timeout_seconds)
        response.raise_for_status()
        frame = pd.read_excel(BytesIO(response.content), engine="openpyxl")
        return [self.normalize_row(row) for row in frame.to_dict(orient="records")]

    def normalize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        title = first_present(row, ["Наименование лота", "Наименование", "Лот", "Предмет торгов", "title"])
        description = first_present(row, ["Описание", "Описание лота", "Предмет", "description"])
        location = first_present(row, ["Местоположение", "Адрес", "location"])
        external_id = first_present(row, ["Номер извещения", "Номер лота", "Реестровый номер", "external_id"])
        url = first_present(row, ["Ссылка", "URL", "url"])
        price = first_present(row, ["Начальная цена", "Цена", "Размер платы", "price_text"])
        publication_date = first_present(row, ["Дата публикации", "Опубликовано", "publication_date"])
        deadline = first_present(row, ["Дата окончания приема заявок", "Окончание приема заявок", "application_deadline"])
        auction_date = first_present(row, ["Дата торгов", "auction_date"])
        status = first_present(row, ["Статус", "status"])
        raw_text = "\n".join(f"{key}: {stringify(value)}" for key, value in row.items() if stringify(value))
        return normalize_item(
            {
                "source": self.name,
                "external_id": external_id,
                "title": title,
                "description": description,
                "location": location,
                "price_text": price,
                "status": status or "new",
                "publication_date": publication_date,
                "application_deadline": deadline,
                "auction_date": auction_date,
                "url": url,
                "raw_text": raw_text,
            }
        )


class VbglenoblSource:
    name = "vbglenobl"

    def __init__(self, list_url: str, http: HttpSettings, pause_seconds: float = 1.0):
        self.list_url = list_url
        self.http = http
        self.pause_seconds = pause_seconds

    def fetch_items(self) -> list[dict[str, Any]]:
        if not self.list_url:
            LOGGER.warning("Vbglenobl source skipped: list_url is empty")
            return []
        response = requests.get(self.list_url, headers=self.http.headers, timeout=self.http.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = self.extract_links(soup)
        items: list[dict[str, Any]] = []
        for url, title in links:
            if not self.maybe_land_notice(title):
                continue
            try:
                items.append(self.fetch_detail(url, title))
                time.sleep(self.pause_seconds)
            except requests.RequestException as error:
                LOGGER.error("Vbglenobl detail fetch failed for %s: %s", url, error)
        return items

    def extract_links(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        links: list[tuple[str, str]] = []
        for anchor in soup.find_all("a"):
            title = anchor.get_text(" ", strip=True)
            href = anchor.get("href")
            if not title or not href:
                continue
            links.append((urljoin(self.list_url, str(href)), title))
        return links

    def maybe_land_notice(self, text: str) -> bool:
        normalized = text.lower()
        keywords = ["земель", "39.18", "аренд", "ижс", "лпх", "садовод"]
        return any(keyword in normalized for keyword in keywords)

    def fetch_detail(self, url: str, title: str) -> dict[str, Any]:
        response = requests.get(url, headers=self.http.headers, timeout=self.http.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        body = soup.get_text("\n", strip=True)
        attachments = [urljoin(url, str(anchor.get("href"))) for anchor in soup.find_all("a") if anchor.get("href")]
        return normalize_item(
            {
                "source": self.name,
                "external_id": url,
                "title": title,
                "description": body[:2000],
                "url": url,
                "raw_text": body + ("\n" + "\n".join(attachments) if attachments else ""),
                "status": "new",
            }
        )


def build_sources(config: dict[str, Any], selected_source: str | None = None) -> list[Any]:
    http_config = config.get("http", {})
    http = HttpSettings(
        timeout_seconds=int(http_config.get("timeout_seconds", 30)),
        user_agent=str(http_config.get("user_agent", "LandMonitor/0.1")),
    )
    sources_config = config.get("sources", {})
    sources: list[Any] = []
    gis = sources_config.get("gis_torgi", {})
    if gis.get("enabled", True) and selected_source in (None, "gis_torgi"):
        sources.append(GisTorgiSource(str(gis.get("excel_url") or ""), http))
    vbg = sources_config.get("vbglenobl", {})
    if vbg.get("enabled", True) and selected_source in (None, "vbglenobl"):
        sources.append(VbglenoblSource(str(vbg.get("list_url") or ""), http))
    return sources
