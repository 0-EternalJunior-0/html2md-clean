# Опції конвертації

`MarkdownOptions` — єдине джерело правди для дефолтів. Об'єкт слід вважати
незмінним: нові варіанти створюй через `with_overrides(**kwargs)`.

```python
from markdown import MarkdownOptions

base = MarkdownOptions()
scraping = base.with_overrides(include_links=False, max_length=200_000)
```

## Видалення шуму

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `remove_nav` | `True` | Видаляти `<nav>`. |
| `remove_header` | `True` | Видаляти `<header>`. |
| `remove_footer` | `True` | Видаляти `<footer>`. |
| `remove_aside` | `True` | Видаляти `<aside>`. |
| `remove_ads` | `True` | Видаляти за `noise_classes` / `noise_ids`. |
| `remove_scripts` | `True` | Видаляти `script`, `style`, `noscript`. |
| `remove_buttons` | `True` | Видаляти `<button>`. |
| `remove_forms` | `False` | Видаляти `<form>`. |
| `remove_hidden` | `True` | Прибирати `aria-hidden`, HTML5 `hidden`, hidden-класи. |
| `remove_display_none` | `False` | Прибирати inline `style="display:none"`. |
| `noise_tags` | набір | Теги для автоматичного видалення. |
| `noise_classes` | набір | CSS-класи для видалення. |
| `noise_ids` | набір | HTML `id` для видалення (substring-match). |
| `dynamic_noise_patterns` | `[]` | Regex-патерни для видалення фрагментів тексту. |

Готові набори: `SAFE_NOISE_CLASSES`, `AGGRESSIVE_NOISE_CLASSES`,
`COMMON_NOISE_PATTERNS` (усі в `markdown.options`).

## Включення контенту

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `include_links` | `True` | Рендерити посилання. |
| `include_images` | `False` | Рендерити зображення. |
| `include_tables` | `True` | Рендерити таблиці. |
| `include_code_blocks` | `True` | Рендерити код. |
| `include_lists` | `True` | Рендерити списки. |
| `include_blockquotes` | `True` | Рендерити цитати. |

## Обмеження та форматування

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `max_length` | `100000` | Максимальна довжина тексту. |
| `min_paragraph_length` | `3` | Мінімальна довжина абзацу. |
| `min_heading_length` | `1` | Мінімальна довжина заголовка. |
| `max_word_length` | `80` | Довші «слова» (CSS/garbage) видаляються. |
| `normalize_whitespace` | `True` | Нормалізація пробілів. |
| `preserve_whitespace` | `False` | Зберігати whitespace як є. |
| `bullets` | `"-"` | Символи bullet'ів по рівнях вкладеності. |
| `newline_style` | `SPACES` | Стиль hard-break для `<br>` (`SPACES`/`BACKSLASH`). |
| `strict_escape` | `False` | Екранувати всі CommonMark-спецсимволи. |

## Посилання та URL

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `link_style` | `INLINE` | `INLINE` `[text](url)` або `REFERENCE` `[text][N]`. |
| `generate_citations` | `False` | Генерувати `markdown_with_citations`. |
| `normalize_urls` | `True` | Абсолютизувати відносні URL. |
| `base_url` | `""` | Базовий URL для абсолютизації. |
| `clean_urls` | `False` | Прибирати UTM/tracker-хвости (courlan). |

## Виділення основного контенту

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `use_content_density` | `False` | Аналіз щільності тексту для main-content. |
| `link_density_threshold` | `0.5` | Поріг link-density для відкидання меню/футерів. |
| `min_content_words` | `100` | Мінімум слів; інакше fallback на повний root. |
| `main_content_min_length` | `200` | Мінімальна довжина кандидата. |
| `main_content_semantic_bonus` | `1.5` | Бонус score для `<article>` / `<main>`. |
| `main_content_noise_penalty` | `0.3` | Штраф score для noise-елементів. |

## Парсер і препроцесинг

| Опція | Дефолт | Опис |
| --- | --- | --- |
| `force_beautifulsoup` | `False` | Форсувати BS4 замість Selectolax. |
| `use_trafilatura_extraction` | `False` | Boilerplate-екстракція через trafilatura. |
| `normalize_unicode` | `False` | NFKC-нормалізація Unicode. |
| `fix_text_encoding` | `False` | Лікування mojibake через ftfy. |
| `sanitize_html` | `False` | Санітизація HTML через nh3. |
| `extract_dates` | `False` | Витяг дат публікації/оновлення (htmldate). |
| `extract_dates_extensive` | `False` | Розширений пошук дат (повільніше). |
| `date_output_format` | `"%Y-%m-%d"` | strftime-формат дат. |

Повний перелік із докладними описами — у сирці
[`markdown/options.py`](https://gitlab.com/demoprogrammer/html2md-clean/-/blob/main/markdown/options.py).
