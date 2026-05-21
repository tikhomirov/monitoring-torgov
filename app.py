from __future__ import annotations

import pandas as pd
import streamlit as st

from land_monitor.config import load_config
from land_monitor.runner import run_once
from land_monitor.storage import LandStore


STATUS_LABELS = {
    "new": "Новый",
    "ignored": "Игнорировать",
    "applied": "Подал заявление",
    "expired": "Истёк срок",
}


@st.cache_data(ttl=30)
def get_config() -> dict:
    return load_config()


def get_store(config: dict) -> LandStore:
    return LandStore(config["database"]["path"])


def is_configured(value: str | None) -> bool:
    return bool(str(value or "").strip())


def render_setup_panel(config: dict, store: LandStore) -> None:
    sources = config.get("sources", {})
    gis_url = sources.get("gis_torgi", {}).get("excel_url")
    vbg_url = sources.get("vbglenobl", {}).get("list_url")

    with st.sidebar:
        st.header("Запуск")
        st.caption("UI показывает базу SQLite. Чтобы появились записи, сначала запустите проверку.")

        st.write("Источники:")
        st.write(f"ГИС Торги Excel: {'✅ задан' if is_configured(gis_url) else '⚠️ не задан'}")
        st.write(f"Выборгский район: {'✅ задан' if is_configured(vbg_url) else '⚠️ не задан'}")

        selected = st.selectbox(
            "Что проверить",
            options=["all", "gis_torgi", "vbglenobl"],
            format_func=lambda value: {
                "all": "Все источники",
                "gis_torgi": "ГИС Торги",
                "vbglenobl": "Выборгский район",
            }[value],
        )

        if st.button("Запустить проверку сейчас", type="primary", use_container_width=True):
            selected_source = None if selected == "all" else selected
            with st.spinner("Проверяю источники и сохраняю новые записи..."):
                result = run_once(config, store=store, selected_source=selected_source, dry_run=False)
            st.success(
                "Проверка завершена: "
                f"получено {result.fetched}, добавлено {result.inserted}, "
                f"релевантных {result.relevant}, уведомлений {result.notified}, ошибок {result.errors}."
            )

        st.divider()


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
        station = st.selectbox("Станция", [""] + stations)
        source = st.selectbox("Источник", [""] + sources)
        status = st.selectbox("Статус", [""] + statuses, format_func=lambda value: STATUS_LABELS.get(value, value))
        min_area_m2 = st.number_input("Минимальная площадь, м²", min_value=0, value=0, step=100)
        only_notified = st.checkbox("Только с уведомлением")
        only_new = st.checkbox("Только новые")

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
        st.info(
            "Записей пока нет. Нажмите «Запустить проверку сейчас» в боковой панели "
            "или выполните `python monitor.py --once` в терминале."
        )
        return None

    frame = pd.DataFrame(items)
    view_columns = [
        "id",
        "publication_date",
        "application_deadline",
        "station_match",
        "area_m2",
        "area_sotka",
        "title",
        "purpose",
        "contract_type",
        "source",
        "status",
        "is_interesting",
        "is_notified",
        "url",
    ]
    frame = frame[[column for column in view_columns if column in frame.columns]]
    frame = frame.rename(
        columns={
            "publication_date": "публикация",
            "application_deadline": "дедлайн",
            "station_match": "станция",
            "area_m2": "м²",
            "area_sotka": "сотки",
            "title": "название",
            "purpose": "назначение",
            "contract_type": "тип",
            "source": "источник",
            "status": "статус",
            "is_interesting": "интересно",
            "is_notified": "уведомлено",
            "url": "ссылка",
        }
    )

    event = st.dataframe(frame, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
    if event.selection.rows:
        return int(frame.iloc[event.selection.rows[0]]["id"])
    return int(frame.iloc[0]["id"])


def render_card(store: LandStore, item_id: int) -> None:
    item = store.get_item(item_id)
    st.subheader(item["title"])

    col1, col2, col3, col4 = st.columns(4)
    col1.write(f"**Станция:** {item.get('station_match') or '-'}")
    col2.write(f"**Площадь:** {item.get('area_m2') or '-'} м²")
    col3.write(f"**Назначение:** {item.get('purpose') or '-'}")
    col4.write(f"**Тип:** {item.get('contract_type') or '-'}")

    st.write(f"**Источник:** {item.get('source') or '-'}")
    st.write(f"**Дедлайн:** {item.get('application_deadline') or '-'}")
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
    st.caption("Радар земельных извещений и торгов под ИЖС/ЛПХ/садоводство рядом со станциями Финляндского направления.")

    config = get_config()
    store = get_store(config)
    store.initialize()

    render_setup_panel(config, store)
    render_metrics(store)
    all_items = store.list_items()
    filters = render_filters(all_items)
    filtered_items = store.list_items(filters)
    selected_id = render_table(filtered_items)
    if selected_id:
        render_card(store, selected_id)


if __name__ == "__main__":
    main()
