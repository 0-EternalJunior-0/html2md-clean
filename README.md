# html2md-clean

> Чистий, керований конвертер **HTML → Markdown** з видаленням «шуму» (реклама, попапи, навігація), розрахований на web-scraping та підготовку тексту для LLM.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Ruff](https://img.shields.io/badge/lint-ruff-46a2f1.svg)](https://docs.astral.sh/ruff/)
[![Tests](https://img.shields.io/badge/tests-pytest-0a9edc.svg)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Зміст

- [Огляд](#огляд)
- [Можливості](#можливості)
- [Встановлення](#встановлення)
- [Швидкий старт](#швидкий-старт)
- [CLI](#cli)
- [Приклади використання](#приклади-використання)
- [Публічний API](#публічний-api)
- [Опції конвертації](#опції-конвертації)
- [Опційні залежності](#опційні-залежності)
- [Продуктивність](#продуктивність)
- [Розробка](#розробка)
- [Тестування](#тестування)
- [Документація](#документація)
- [Ліцензія](#ліцензія)

---

## Огляд

`html2md-clean` перетворює «брудний» HTML реальних вебсторінок на чистий Markdown.
На відміну від простих конвертерів, бібліотека спершу **прибирає boilerplate** —
навігацію, футери, банери, cookie-попапи, рекламні блоки — а вже потім рендерить
основний контент. Це робить її зручною для:

- **web-scraping** та побудови датасетів;
- підготовки тексту для **RAG / LLM**-пайплайнів (менше токенів шуму);
- **архівування** статей у читабельному Markdown.

Бібліотека працює на двох парсерах: **Selectolax** (швидкий, за замовчуванням, якщо
встановлений) та **BeautifulSoup** (fallback), схованих за єдиним `Adapter`-інтерфейсом.

## Можливості

- 🧹 **Очищення шуму** за тегами, CSS-класами, `id`, `aria-hidden`, inline `display:none`.
- 🧠 **Виділення основного контенту** через link-density та content-density евристики.
- 🔗 **Посилання**: inline `[text](url)` або reference-style `[text][N]`, опційне очищення UTM/tracker-хвостів (courlan).
- 📚 **Цитати**: варіант Markdown із виносками `[1]`, `[2]` + список джерел.
- 🧾 **Метадані**: `title`, перший `h1`, `description`, лічильники слів/символів/заголовків/посилань.
- 📅 **Дати публікації/оновлення** (опційно, через `htmldate`).
- 🩹 **Лікування mojibake** (`ftfy`), NFKC-нормалізація Unicode, HTML-санітизація (`nh3`).
- ⚡ **Синхронний та асинхронний** API, ліниво-генерований `raw_markdown`.
- 🎛️ **Immutable-опції** (`MarkdownOptions.with_overrides(...)`) — безпечні для потоків.

## Встановлення

Потрібен **Python 3.11+**.

```bash
pip install html2md-clean
```

Разом з опційними «батарейками» (дати, санітизація, encoding-fix, очищення URL):

```bash
pip install "html2md-clean[full]"
```

Встановлення з GitLab-репозиторію:

```bash
pip install git+https://gitlab.com/demoprogrammer/html2md-clean.git
```

## Швидкий старт

```python
from markdown import MarkdownGenerator

html = """
<html><body>
  <nav>меню сайту</nav>
  <article>
    <h1>Заголовок статті</h1>
    <p>Це основний абзац із корисним текстом.</p>
  </article>
  <footer>© 2026</footer>
</body></html>
"""

generator = MarkdownGenerator()
result = generator.generate_from_html(html)

print(result.fit_markdown)
# # Заголовок статті
#
# Це основний абзац із корисним текстом.

print(result.word_count, result.h1)
```

Найкоротший варіант:

```python
from markdown import MarkdownGenerator

result = MarkdownGenerator.quick_generate(html)
print(result.markdown)  # аліас для fit_markdown
```

## CLI

Після встановлення доступна команда `html2md`:

```bash
# з файлу у stdout
html2md page.html

# зі stdin у файл
cat page.html | html2md -o page.md

# зберегти посилання (за замовчуванням вимкнено у CLI-профілі)
html2md page.html --include-links

# форсувати BeautifulSoup замість Selectolax
html2md page.html --force-bs4
```

Аналогічно можна запускати як модуль без встановлення:

```bash
python main_service.py page.html -o page.md
```

## Приклади використання

### Кастомні опції

```python
from markdown import MarkdownGenerator, MarkdownOptions

options = MarkdownOptions(
    include_links=True,
    include_images=True,
    generate_citations=True,
    max_length=50_000,
    clean_urls=True,          # прибрати utm_*, fbclid, gclid
    base_url="https://example.com",
)

generator = MarkdownGenerator(options)
result = generator.generate_from_html(html)

print(result.markdown_with_citations)
for ref in result.references:
    print(ref)
```

### Reference-style посилання

```python
from markdown import MarkdownGenerator, MarkdownOptions
from markdown.options import LinkStyle

options = MarkdownOptions(link_style=LinkStyle.REFERENCE)
result = MarkdownGenerator(options).generate_from_html(html)
```

### Асинхронний виклик

```python
import asyncio
from markdown import generate_markdown_async

async def run():
    result = await generate_markdown_async(html)
    print(result.fit_markdown)

asyncio.run(run())
```

### Витяг дат публікації (опційно)

```python
from markdown import MarkdownGenerator, MarkdownOptions

options = MarkdownOptions(extract_dates=True)
result = MarkdownGenerator(options).generate_from_html(html)
print(result.published_date, result.updated_date)
```

### Фасад під web-scraping

```python
from main_service import HTMLToMarkdownConverter

converter = HTMLToMarkdownConverter()   # агресивніші дефолти під scraping
markdown = converter.convert(html)
```

### Реальний приклад: налаштування `MarkdownOptions` під scraping блогу

Нижче — як це роблять «по-справжньому»: беремо HTML новинної/блогової сторінки,
свідомо вмикаємо/вимикаємо потрібні опції та пояснюємо, **навіщо** кожна з них.

```python
from markdown import MarkdownGenerator, MarkdownOptions
from markdown.options import LinkStyle, AGGRESSIVE_NOISE_CLASSES, COMMON_NOISE_PATTERNS

options = MarkdownOptions(
    # --- виділення основного контенту ---
    use_content_density=True,       # шукати <article>/<main>, а не весь <body>
    link_density_threshold=0.4,     # жорсткіше відкидати меню/футери (більше посилань = шум)
    min_content_words=40,           # короткі блоки не вважати основним контентом

    # --- очищення шуму ---
    remove_ads=True,
    noise_classes=AGGRESSIVE_NOISE_CLASSES,   # + sidebar/related/comments/carousel
    remove_display_none=True,                 # прибрати приховані inline-блоки
    dynamic_noise_patterns=COMMON_NOISE_PATTERNS,  # "5 хв тому", "Apply now", лічильники

    # --- що лишаємо в Markdown ---
    include_links=True,
    include_images=True,
    include_tables=True,
    generate_citations=True,        # зробити варіант із виносками [1], [2]

    # --- посилання та URL ---
    link_style=LinkStyle.REFERENCE, # у довгих статтях чистіше, ніж inline
    normalize_urls=True,
    base_url="https://example-blog.com",  # відносні /article → абсолютні
    clean_urls=True,                # прибрати utm_*, fbclid, gclid

    # --- нормалізація тексту ---
    fix_text_encoding=True,         # полікувати mojibake (потрібен ftfy)
    normalize_unicode=True,         # fullwidth/лігатури → ASCII (NFKC)
    max_length=200_000,             # довгі лонгріди не обрізати завчасно
)

generator = MarkdownGenerator(options)
result = generator.generate_from_html(html)

print(result.markdown_with_citations)   # текст із [1], [2]
print("слів:", result.word_count, "| посилань:", result.rendered_link_count)
for ref in result.references:
    print(ref)   # {'id': 1, 'text': '...', 'url': '...'}
```

> 💡 **Порада.** Конфіг незмінний, тож зберігай один «базовий» профіль і роби
> точкові варіації через `with_overrides` — без дублювання всього набору:
>
> ```python
> BASE = MarkdownOptions(use_content_density=True, include_links=True)
>
> # для e-commerce-карток: коротший поріг довжини кандидата
> ecommerce = BASE.with_overrides(main_content_min_length=100, include_images=True)
>
> # для «сирого» дампу без фільтрації посилань
> raw_dump = BASE.with_overrides(include_links=False, use_content_density=False)
> ```


## Публічний API

Імпорт: `from markdown import ...`

| Об'єкт | Призначення |
| --- | --- |
| `MarkdownGenerator` | Головний генератор. `generate_from_html(html) -> MarkdownResult`, `quick_generate(html)`, `generate(source)`. |
| `MarkdownOptions` | Immutable-конфіг конвертації. Використовуй `with_overrides(**kwargs)`. |
| `MarkdownResult` | Результат: `fit_markdown`, `raw_markdown` (лениво), `markdown_with_citations`, метадані та лічильники. |
| `generate_markdown_async(html, options=None)` | Асинхронна обгортка (thread executor). |
| `configure_logging(level=WARNING)` | Налаштування логера пакета. |
| `COMMON_NOISE_PATTERNS` | Готовий набір regex для `dynamic_noise_patterns`. |

Ключові поля `MarkdownResult`:

| Поле | Тип | Опис |
| --- | --- | --- |
| `fit_markdown` / `markdown` | `str` | Основний очищений Markdown. |
| `raw_markdown` | `str` | Повний Markdown без агресивної фільтрації (ленива генерація). |
| `markdown_with_citations` | `str` | Варіант із виносками `[1]`, `[2]`. |
| `references` | `list[dict]` | Список джерел для цитат. |
| `title`, `h1`, `description` | `str` | Метадані сторінки. |
| `word_count`, `char_count`, `heading_count`, `link_count`, `image_count` | `int` | Статистика. |
| `published_date`, `updated_date` | `str \| None` | Дати (лише з `extract_dates=True`). |
| `is_truncated` | `bool` | Чи текст обрізаний до `max_length`. |

## Опції конвертації

`MarkdownOptions` — єдине джерело правди для дефолтів. Найчастіші:

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `remove_nav` / `remove_header` / `remove_footer` / `remove_aside` | `True` | Видалення відповідних семантичних блоків. |
| `remove_ads` | `True` | Видалення за `noise_classes` / `noise_ids`. |
| `remove_hidden` | `True` | Прибирати `aria-hidden`, HTML5 `hidden`, hidden-класи. |
| `include_links` | `True` | Рендерити посилання. |
| `include_images` | `False` | Рендерити зображення. |
| `include_tables` / `include_lists` / `include_code_blocks` / `include_blockquotes` | `True` | Підтримка відповідних елементів. |
| `max_length` | `100000` | Максимальна довжина тексту. |
| `min_paragraph_length` | `3` | Мінімальна довжина абзацу. |
| `generate_citations` | `False` | Генерувати `markdown_with_citations`. |
| `link_style` | `INLINE` | `INLINE` або `REFERENCE`. |
| `clean_urls` | `False` | Прибирати UTM/tracker-параметри (courlan). |
| `normalize_urls` / `base_url` | `True` / `""` | Абсолютизація відносних URL. |
| `use_content_density` | `False` | Евристика виділення основного контенту. |
| `link_density_threshold` | `0.5` | Поріг link-density для відкидання меню/футерів. |
| `force_beautifulsoup` | `False` | Форсувати BS4 замість Selectolax. |

Повний перелік — у [`markdown/options.py`](markdown/options.py) та в [документації](#документація).

Опції незмінні: створюй нові варіанти через `with_overrides`:

```python
base = MarkdownOptions()
scraping = base.with_overrides(include_links=False, max_length=200_000)
```

## Опційні залежності

Деякі можливості вмикаються встановленням додаткових пакетів (бібліотека
gracefully деградує, якщо їх немає):

| Можливість | Опція | Пакет |
| --- | --- | --- |
| Витяг дат | `extract_dates` | `htmldate` |
| Санітизація HTML | `sanitize_html` | `nh3` |
| Лікування mojibake | `fix_text_encoding` | `ftfy` |
| Очищення URL | `clean_urls` | `courlan` |
| Boilerplate-екстракція | `use_trafilatura_extraction` | `trafilatura` |
| Швидкий парсер | — (авто) | `selectolax` |

## Продуктивність

- **Selectolax** використовується автоматично, якщо встановлений, і дає суттєвий приріст швидкості проти BeautifulSoup.
- `raw_markdown` генерується **лениво** — платиш за нього лише при доступі.
- `MarkdownOptions` — immutable, тож інстанси генератора безпечно шарити між потоками.

Бенчмарки — у теці [`test/`](test/) (`benchmark.py`, `benchmark_html2md.py`, `test_benchmarks.py`).

## Розробка

```bash
git clone https://gitlab.com/demoprogrammer/html2md-clean.git
cd html2md-clean

python -m venv .venv && source .venv/bin/activate
pip install -e ".[full,dev]"
```

Лінтер (конфіг у [`ruff.toml`](ruff.toml)):

```bash
ruff check .
ruff format --diff .
```

## Тестування

```bash
pytest              # весь набір
pytest -q test/test_generator.py
```

Конфіг у [`pytest.ini`](pytest.ini) (`asyncio_mode = auto`). Набір містить unit-,
integration-, property- (Hypothesis) та stress-тести.

## Документація

Документація збирається через **MkDocs** (Material theme):

```bash
pip install mkdocs mkdocs-material
mkdocs serve      # локальний перегляд на http://127.0.0.1:8000
mkdocs build      # статична збірка у site/
```

Джерела — у теці [`docs/`](docs/), конфіг — [`mkdocs.yml`](mkdocs.yml).

## Ліцензія

Розповсюджується за ліцензією **MIT**. Деталі — у файлі [LICENSE](LICENSE).
