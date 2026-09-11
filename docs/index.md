# html2md-clean

**Чистий, керований конвертер HTML → Markdown** з видаленням «шуму» (реклама,
попапи, навігація, футери), розрахований на web-scraping та підготовку тексту
для LLM.

## Навіщо

Реальні вебсторінки повні boilerplate: меню, банери, cookie-попапи, блоки
«читайте також». `html2md-clean` спершу прибирає цей шум, а вже потім рендерить
основний контент у чистий Markdown — менше токенів, більше сигналу.

## Ключові можливості

- 🧹 Очищення шуму за тегами, класами, `id`, `aria-hidden`, `display:none`.
- 🧠 Виділення основного контенту (link-density / content-density евристики).
- 🔗 Inline та reference-style посилання, очищення UTM/tracker-хвостів.
- 📚 Markdown із виносками-цитатами `[1]`, `[2]` та списком джерел.
- 🧾 Метадані (`title`, `h1`, `description`) і лічильники.
- 📅 Опційний витяг дат публікації/оновлення.
- ⚡ Синхронний та асинхронний API, два парсери (Selectolax / BeautifulSoup).

## Швидкий погляд

```python
from markdown import MarkdownGenerator

result = MarkdownGenerator().generate_from_html("<h1>Привіт</h1><p>Світ.</p>")
print(result.fit_markdown)
```

Далі: [Встановлення](installation.md) · [Швидкий старт](quickstart.md) ·
[CLI](cli.md) · [Опції](options.md) · [API](api.md).
