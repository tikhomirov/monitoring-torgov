# Land Monitor

Локальный мониторинг земельных лотов по ГИС Торги и объявлениям администрации Выборгского района. Система ищет участки от 1000 м² рядом со станциями Финляндского направления, сохраняет новые записи в SQLite, показывает их в Streamlit UI и отправляет Telegram-уведомления.

## Установка

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Настройка `.env`

```dotenv
GIS_TORGI_EXCEL_URL=https://example/export.xlsx
VBGLENOBL_LIST_URL=https://example/notices
LAND_MONITOR_DB=data/land_monitor.sqlite3
TELEGRAM_BOT_TOKEN=123456:token
TELEGRAM_CHAT_ID=123456789
```

`TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` необязательны. Если они пустые, мониторинг работает без уведомлений.

## Настройка `config.yaml`

Главные параметры:

- `database.path` — путь к SQLite-файлу.
- `exports.path` — путь экспорта Excel.
- `sources.gis_torgi.excel_url` — URL публичной Excel-выгрузки ГИС Торги.
- `sources.vbglenobl.list_url` — URL доски объявлений / извещений администрации.
- `filters.min_area_m2` — минимальная площадь, по умолчанию `1000`.
- `filters.stations` — станции для поиска.
- `filters.positive_keywords` и `filters.negative_keywords` — словари релевантности.

Переменные из `.env` переопределяют URL источников и путь к БД.

## Ручной запуск проверки

```bash
python monitor.py --once
```

Запуск одного источника:

```bash
python monitor.py --once --source gis_torgi
python monitor.py --once --source vbglenobl
```

Сухой запуск без записи в SQLite:

```bash
python monitor.py --once --dry-run
```

Проверка с экспортом:

```bash
python monitor.py --once --export
python monitor.py --once --export data/land_items.csv
```

## Запуск UI

```bash
streamlit run app.py
```

Откройте http://localhost:8501. В интерфейсе доступны метрики, фильтры, таблица записей, карточка выбранной записи и кнопки статусов.

## Cron

Пример запуска каждые 6 часов:

```cron
0 */6 * * * cd /path/to/land-monitor && /usr/bin/python3 monitor.py --once
```

## Docker

```bash
docker compose up --build
```

UI будет доступен на порту `8501`, каталог `./data` подключается как volume, переменные берутся из `.env`.

## Тесты

```bash
pytest
```

Тесты покрывают парсинг площади, фильтрацию, дедупликацию SQLite, обновление статусов и базовый pipeline запуска.

## Схема SQLite

Таблица `land_items` создаётся автоматически и содержит поля из ТЗ: источник, внешний ID, название, описание, локацию, станцию, площадь, назначение, тип договора, цены, даты, URL, сырой текст, `content_hash`, признаки интересности и уведомления, даты создания и обновления.
