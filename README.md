# Avito Ads Parser

Pipeline for processing Avito marketplace advertisements: `HTML (Авито) -> парсинг -> API обогащение -> анализ покрытия`

## Обзор проекта

Этот проект реализует пайплайн для:
1. Парсинга HTML-страниц Авито для извлечения объявлений
2. Обогащения объявлений через API (классификация по категориям, брендам, моделям)
3. Анализа покрытия каталога и выявления недостающих комбинаций

## Структура проекта

```
avito-ads-parser/
+-- data/
|   +-- site1.html           # Входные HTML-файлы
|   +-- site2.html           # Входные HTML-файлы
|   +-- output.csv           # Целевой каталог (3499 строк)
|   +-- ads_raw.csv          # Спаршенные объявления
|   +-- ads_enriched.csv     # Обогащённые объявления
+-- logs/
|   +-- api_log.txt          # Логи API запросов
+-- src/
|   +-- parser.py            # Парсер HTML
|   +-- enricher.py          # API клиент
|   +-- analyzer.py          # Анализатор покрытия
+-- main.py                  # Точка входа
+-- pyproject.toml           # Зависимости (uv)
+-- README.md                # Документация
```

## Установка

### Требования
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - менеджер пакетов

### Установка зависимостей
```bash
uv sync
```

## Использование

### Запуск полного пайплайна
```bash
uv run python main.py
```

### Выходные файлы
- `data/ads_raw.csv` - сырые данные из HTML
- `data/ads_enriched.csv` - обогащённые через API
- `data/missing_coverage.csv` - недостающие комбинации
- `logs/api_log.txt` - логи API запросов

## Детали реализации

### 1. Парсинг HTML (`src/parser.py`)

**Метод:** BeautifulSoup + lxml

**Извлекаемые поля:**
| Поле | Источник | Обязательное |
|------|----------|--------------|
| `ad_id` | `data-item-id` | Да |
| `title` | `data-marker="item-title"` | Да |
| `url` | `href` в теге с title | Нет |
| `region` | `data-marker="item-location"` | Нет |
| `price` | `data-marker="item-price"` | Нет |

**Пример извлечения:**
```python
from src.parser import parse_html_files

ads = parse_html_files(['data/site1.html', 'data/site2.html'])
for ad in ads:
    print(f"{ad.ad_id}: {ad.title}")
```

### 2. Обогащение через API (`src/enricher.py`)

**API детали:**
- **URL:** `https://top505.ru/api/item_batch`
- **Method:** POST
- **Headers:** `X-API-Key: "<ваш-API-ключ>"` (задаётся через переменную окружения `TOP505_API_KEY`)
- **Rate limit:** 2-5 req/s (реализована задержка 0.5s)

**Формат запроса:**
```json
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

**Пример ответа:**
```json
{
  "processed_data": [
    {
      "title": "Натяжитель гусеницы CAT 312 / 188-0895",
      "marka": "cat",
      "model": "312",
      "catalog_number": "188-0895",
      "group0": "ходовая часть",
      "group1": "натяжитель",
      "group2": "натяжитель в сборе",
      "group3": null,
      "group4": null,
      ...
    }
  ]
}
```

**Обработка ошибок:**
| Код | Обработка |
|-----|-----------|
| 200 | Успех |
| 401 | Логирование ошибки auth |
| 429 | Экспоненциальная пауза + retry |
| 5xx | Retry до 3 раз |
| Timeout | Retry до 3 раз |
| Не-JSON | Логирование + пропуск |

**Логирование:**
- Количество отправленных запросов
- Успешные/неуспешные
- % успеха
- Типы ошибок
- Количество retry

### 3. Анализ покрытия (`src/analyzer.py`)

**Логика сравнения:**
1. Из `ads_enriched.csv` берём уникальные комбинации `group0 + group1 + group2`
2. Из `output.csv` берём целевые комбинации
3. Находим разницу (merge + indicator)
4. Сортируем по частоте в целевом каталоге

**Выходные колонки:**
```csv
group0,group1,group2,marka,model,reason
ходовая часть,каток опорный,,,отсутствует
гидравлический компонент,насос,hyundai,отсутствует
```

## Примеры использования

### Только парсинг HTML
```python
from src.parser import parse_html_files
import pandas as pd

ads = parse_html_files(['data/site1.html'])
df = pd.DataFrame([ad.to_dict() for ad in ads])
df.to_csv('my_ads.csv', index=False)
```

### Только обогащение
```python
import asyncio
from src.enricher import enrich_all_ads

ads_df = pd.read_csv('my_ads.csv')
enriched, stats = await enrich_all_ads(
    ads_df.to_dict('records'),
    batch_size=200,
    rate_limit_delay=0.5
)
```

### Только анализ покрытия
```python
from src.analyzer import generate_coverage_report

report = generate_coverage_report(
    'data/ads_enriched.csv',
    'data/output.csv'
)
print(f"Coverage: {report['coverage_percentage']}%")
```

## Результаты запуска

```
=== Pipeline Summary ===
Found 100 ads across 2 files
Successfully enriched 90/100 items (90.0%)
Coverage: 6.96% (8/115 combinations)
Missing: 107 combinations
```

## Возможные улучшения (1-2 недели)

1. **CLI интерфейс** - argparse для гибкости запуска
2. **Конфигурация** - config.yaml для настроек API
3. **Кеширование** - не дергать API повторно (sqlite/redis)
4. **Больше метрик** - статистика по брендам, категориям
5. **Тесты** - pytest для критических функций
6. **Docker** - контейнеризация для деплоя
7. **Airflow/Prefect** - оркестрация пайплайна
8. **Прогресс-бар** - tqdm для визуализации прогресса
9. **Параллелизация** - asyncio для парсинга множества файлов
10. **Валидация** - pydantic для валидации данных
