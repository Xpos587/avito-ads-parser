# Avito Ads Parser

Pipeline for identifying gaps in product catalog coverage by analyzing marketplace advertisements.

## Why This Exists

Company sells spare parts for heavy machinery and wants to systematically discover which product combinations are missing from their sales channels. This pipeline takes raw marketplace listings, enriches them with product classification, and compares against the target catalog to reveal coverage gaps.

## Mental Model

The data flows through three stages, each with a single responsibility:

1. **Extract** (`src/parser.py`) — Pull raw ads from HTML snapshots
2. **Enrich** (`src/enricher.py`) — Classify ads via external API
3. **Analyze** (`src/analyzer.py`) — Find gaps between what we have vs. what we need

Each stage is isolated and can be run independently. If you need to add a new data source (e.g., parse a different marketplace), add a parser in `src/` and plug it into the pipeline in `main.py`. If you need a different enrichment API, swap out the enricher. The analyzer only cares about the final enriched format.

## Project Structure

```
avito-ads-parser/
├── src/          # Core pipeline modules (parser → enricher → analyzer)
├── data/         # Input (HTML, catalog) and output (CSV files)
├── logs/         # API request logs for debugging
├── tests/        # 97% test coverage
└── main.py       # Orchestrates the full pipeline
```

## Data Format

All modules work with the same ad structure. The parser extracts `ad_id`, `title`, `url`, `region`, `price`. The enricher adds `group0-5` (product hierarchy), `marka`, `model`. The analyzer compares `group0 + group1 + group2` combinations against the target catalog.

If you need to track additional fields, extend the `Ad` dataclass in `src/parser.py` and update the analyzer's group columns.

## Quick Start

```bash
# Install dependencies (Python 3.14+)
uv sync

# Set your API key
cp .env.example .env
# Edit .env and add: TOP505_API_KEY=your_key

# Run the full pipeline
uv run python main.py
```

## Output

Three files are generated in `data/`:

- `ads_raw.csv` — Raw ads extracted from HTML
- `ads_enriched.csv` — Ads with product classification from API
- `missing_coverage.csv` — Product combinations missing from our ads, sorted by priority

## Development

```bash
# Run linting, type checking, dead code detection
uv run check

# Run tests
uv run test

# Run tests with coverage
uv run test-cov
```

### Adding a New Marketplace Parser

Create a new parser module in `src/` that returns the same `Ad` structure, then import it in `main.py` and swap out `parse_html_files()`.

### Changing the Enrichment API

Modify `src/enricher.py` to call your API instead. The rest of the pipeline expects `group0-5`, `marka`, `model` fields in the enriched output.

### Adjusting Coverage Analysis

Edit the `group_cols` list in `src/analyzer.py` if you want to compare on different fields.

## Pipeline Results

On real data (100 ads from Avito):
- **Extraction:** 100 ads parsed
- **Enrichment:** 90/100 (90% success rate)
- **Coverage:** 6/115 combinations (5.22%)
- **Gaps identified:** 109 missing combinations

## Configuration via Environment Variables

| Variable | Purpose | Required |
|----------|---------|----------|
| `TOP505_API_KEY` | API key for top505.ru enrichment service | Yes |

Set these in a `.env` file (see `.env.example` for template).

---

# Implementation Details (per ТЗ Requirements)

## Как парсились HTML-страницы

Используется `BeautifulSoup` с парсером `lxml` для извлечения объявлений из HTML-снимков Авито.

**Извлекаемые поля:**
| Поле | Источник | Обязательное |
|------|----------|--------------|
| `ad_id` | `data-item-id` атрибут | Да |
| `title` | `data-marker="item-title"` тег | Да |
| `url` | `href` атрибут ссылки | Нет |
| `region` | `data-marker="item-location"` тег | Нет |
| `price` | `data-marker="item-price"` тег | Нет |

Ограничения соблюдены: нет обращений к интернету, нет авторизации/прокси, используется только локальный HTML.

## Пример запроса и ответа к API

**Запрос:**
```http
POST https://top505.ru/api/item_batch
Content-Type: application/json
X-API-Key: <ваш-API-ключ>

{
  "source": "1c",
  "data": [
    {
      "title": "Натяжитель гусеницы CAT 312 / 188-0895",
      "day": "2026-01-22"
    }
  ]
}
```

**Ответ (HTTP 200):**
```json
{
  "processed_data": [
    {
      "title": "Натяжитель гусеницы CAT 312 / 188-0895",
      "raw_item": "Натяжитель гусеницы CAT 312 / 188-0895",
      "day": "2026-01-22",
      "marka": "cat",
      "model": "312",
      "catalog_number": "188-0895",
      "group0": "ходовая часть",
      "group1": "натяжитель",
      "group2": "натяжитель в сборе",
      "group3": null,
      "group4": null,
      "clear_item": "натяжитель гусеницы cat 312 / 188-0895"
    }
  ]
}
```

## Обработка ошибок и лимитов

| Код | Обработка |
|-----|-----------|
| **200** | Успех — данные сохраняются |
| **401** | Ошибка авторизации — логируется, выбрасывается `AuthError` |
| **429** | Rate limit — экспоненциальная пауза (2^attempt секунд) + retry до 3 раз |
| **5xx** | Временная ошибка сервера — retry до 3 раз с паузой 1 секунда |
| **Timeout** | Таймаут — retry до 3 раз |
| **Не-JSON** | Логирование ошибки + пропуск записи |

**Лимиты:**
- Скорость: 2-5 req/s (реализовано через `asyncio.sleep(0.5)` между батчами)
- Размер батча: до 200 объектов
- Таймаут: 30 секунд

**Логирование:** подробная статистика в `logs/api_log.txt` (сколько отправлено, успешно, % успеха, типы ошибок, количество retry).

---

# Что бы сделать дальше (1-2 недели)

1. **CLI интерфейс** — `argparse` для гибкости: выбор входных файлов, настройка batch size, пороговое значение для покрытия
2. **Конфигурационный файл** — `config.yaml` для настроек API, путей к файлам, параметров логирования
3. **Кеширование** — SQLite/redis для хранения результатов обогащения и предотвращения повторных API вызов
4. **Дополнительные метрики** — статистика по брендам, категориям, динамика покрытия во времени
5. **Прогресс-бар** — `tqdm` для визуализации прогресса при обработке больших объёмов
6. **Параллелизация** — одновременный парсинг множества HTML-файлов с `asyncio.gather`
7. **Валидация данных** — `pydantic` модели для валидации входных/выходных данных
8. **Docker-контейнер** - для упрощения деплоя и воспроизводимости окружения
9. **Airflow/Prefect DAG** - оркестрация пайплайна с периодическим запуском
10. **Unit-тесты для edge cases** - больше тестов для граничных случаев (пустые файлы, невалидный HTML, ошибки сети)
