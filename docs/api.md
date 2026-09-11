# Публічний API

Імпорт: `from markdown import ...`

## Об'єкти верхнього рівня

| Об'єкт | Призначення |
| --- | --- |
| `MarkdownGenerator` | Головний генератор HTML → Markdown. |
| `MarkdownOptions` | Immutable-конфіг конвертації. |
| `MarkdownResult` | Результат генерації з метаданими та лічильниками. |
| `generate_markdown_async(html, options=None)` | Асинхронна обгортка. |
| `configure_logging(level=WARNING)` | Налаштування логера пакета. |
| `COMMON_NOISE_PATTERNS` | Готовий набір regex для `dynamic_noise_patterns`. |

## `MarkdownGenerator`

```python
class MarkdownGenerator:
    def __init__(self, options: MarkdownOptions | None = None): ...

    @staticmethod
    def quick_generate(html: str) -> MarkdownResult: ...

    def generate(self, source: str | Adapter) -> MarkdownResult: ...
    def generate_from_html(self, html: str) -> MarkdownResult: ...
    def generate_from_adapter(self, adapter) -> MarkdownResult: ...
```

- **`generate_from_html(html)`** — основний вхід. Порожній/пробільний HTML
  повертає `MarkdownResult.empty()`.
- **`quick_generate(html)`** — статичний шорткат із дефолтними опціями.
- **`generate(source)`** — універсальний вхід: рядок HTML або готовий adapter.

Selectolax використовується автоматично, якщо встановлений; інакше — BeautifulSoup.
Форсувати BS4 можна через `MarkdownOptions(force_beautifulsoup=True)`.

## `MarkdownResult`

| Поле / властивість | Тип | Опис |
| --- | --- | --- |
| `fit_markdown` | `str` | Основний очищений Markdown. |
| `markdown` | `str` | Аліас для `fit_markdown`. |
| `raw_markdown` | `str` | Повний Markdown (ленива генерація при доступі). |
| `text` | `str` | Чистий текст без форматування. |
| `markdown_with_citations` | `str` | Варіант із виносками `[1]`, `[2]`. |
| `references` | `list[dict]` | Список джерел для цитат. |
| `title` | `str` | Title сторінки. |
| `h1` | `str` | Перший H1. |
| `description` | `str` | Meta description. |
| `word_count` | `int` | Кількість слів. |
| `char_count` | `int` | Кількість символів. |
| `heading_count` | `int` | Кількість заголовків. |
| `link_count` | `int` | Кількість посилань. |
| `rendered_link_count` | `int` | Посилань, реально вставлених у Markdown. |
| `image_count` | `int` | Кількість зображень. |
| `is_truncated` | `bool` | Чи текст обрізаний до `max_length`. |
| `published_date` | `str \| None` | Дата публікації (лише з `extract_dates`). |
| `updated_date` | `str \| None` | Дата оновлення (лише з `extract_dates`). |

Методи:

- `to_dict()` — серіалізація у `dict` (включно з `raw_markdown`).
- `MarkdownResult.empty()` — порожній результат.
- `bool(result)` — `True`, якщо є `text` або `fit_markdown`.

```python
result = MarkdownGenerator().generate_from_html(html)
print(result.fit_markdown)
print(result.to_dict())
```

## `MarkdownOptions`

Immutable-конфіг. Створюй похідні варіанти через `with_overrides`:

```python
from markdown import MarkdownOptions

options = MarkdownOptions().with_overrides(include_links=False, max_length=200_000)
```

Повний перелік полів — на сторінці [Опції](options.md).

## Асинхронний API

```python
import asyncio
from markdown import generate_markdown_async

result = asyncio.run(generate_markdown_async(html))
```

Виконується в thread executor (`asyncio.to_thread`), не блокує event loop.

## Логування

```python
import logging
from markdown import configure_logging

configure_logging(logging.INFO)
```

За замовчуванням логер пакета `markdown` має `NullHandler` — бібліотека мовчить,
доки логування явно не увімкнено.
