from __future__ import annotations

import pandas as pd
import streamlit as st

from land_monitor.config import load_config
from land_monitor.storage import LandStore


STATUS_LABELS = {
    "new": "Новый",
    "ignored": "Игнорировать",
    "applied": "Подал заявление",
    "expired": "Истёк срок",
}


def get_store() -> LandStore:
    config = load_config()
    return LandStore(config["database"]["path"])


def render_metrics(store: LandStore) -> None:
    metrics = store.metrics()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Всего записей", metrics["total"])
    col2.metric("Новых", metrics["new"])
    col3.metric("Интересных", metrics["interesting"])
    col4.metric("Дедлайн ≤ 7 дней", metrics["upcoming_deadlines"])


def render_filters(items: list[dict]) -> dict:
    stations = sorted({item.get("station_match") for item in items if item.get("station_match")})
    sources = sorted({item.get("source") for item in items if item.get("source")})
    statuses = sorted({item.get("status") for item in items if item.get("status")})

    with st.sidebar:
        st.header("Фильтры")
        station = st.selectbox("station_match", [""] + stations)
        source = st.selectbox("source", [""] + sources)
        status = st.selectbox("status", [""] + statuses)
        min_area_m2 = st.number_input("min_area_m2", min_value=0, value=0, step=100)
        only_notified = st.checkbox("only_notified")
        only_new = st.checkbox("only_new")

    return {
        "station_match": station,
        "source": source,
        "status": status,
        "min_area_m2": min_area_m2 or None,
        "only_notified": only_notified,
        "only_new": only_new,
    }


def render_table(items: list[dict]) -> int | None:
    if not items:
        st.info("Записей пока нет. Запустите `python monitor.py --once`.")
        return None
    frame = pd.DataFrame(items)
    view_columns = [
        "id",
        "publication_date",
        "application_deadline",
        "station_match",
        "area_m2",
        "title",
        "purpose",
        "contract_type",
        "source",
        "status",
        "url",
    ]
    frame = frame[[column for column in view_columns if column in frame.columns]]
    event = st.dataframe(frame, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
    if event.selection.rows:
        return int(frame.iloc[event.selection.rows[0]]["id"])
    return int(frame.iloc[0]["id"])


def render_card(store: LandStore, item_id: int) -> None:
    item = store.get_item(item_id)
    st.subheader(item["title"])
    st.write(f"Станция: {item.get('station_match') or '-'}")
    st.write(f"Площадь: {item.get('area_m2') or '-'} м²")
    st.write(f"Источник: {item.get('source') or '-'}")
    if item.get("url"):
        st.link_button("Открыть оригинал", item["url"])
    st.text_area("Полный текст", item.get("raw_text") or item.get("description") or "", height=280)

    col1, col2, col3, col4 = st.columns(4)
    if col1.button("Пометить интересно"):
        store.set_interesting(item_id, True)
        st.rerun()
    if col2.button("Игнорировать"):
        store.update_status(item_id, "ignored")
        st.rerun()
    if col3.button("Подал заявление"):
        store.update_status(item_id, "applied")
        st.rerun()
    if col4.button("Истёк срок"):
        store.update_status(item_id, "expired")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Land Monitor", layout="wide")
    st.title("Land Monitor")
    store = get_store()
    store.initialize()
    render_metrics(store)
    all_items = store.list_items()
    filters = render_filters(all_items)
    filtered_items = store.list_items(filters)
    selected_id = render_table(filtered_items)
    if selected_id:
        render_card(store, selected_id)


if __name__ == "__main__":
    main()
