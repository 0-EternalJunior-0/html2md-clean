# Швидкий старт

## Базовий приклад

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

result = MarkdownGenerator().generate_from_html(html)
print(result.fit_markdown)
print(result.word_count, result.h1)
```

Навігацію та футер прибрано автоматично.

## Найкоротший варіант

```python
from markdown import MarkdownGenerator

result = MarkdownGenerator.quick_generate(html)
print(result.markdown)  # аліас для fit_markdown
```

## Кастомні опції

```python
from markdown import MarkdownGenerator, MarkdownOptions

options = MarkdownOptions(
    include_links=True,
    include_images=True,
    generate_citations=True,
    max_length=50_000,
    clean_urls=True,
    base_url="https://example.com",
)

result = MarkdownGenerator(options).generate_from_html(html)
print(result.markdown_with_citations)
for ref in result.references:
    print(ref)
```

## Reference-style посилання

```python
from markdown import MarkdownGenerator, MarkdownOptions
from markdown.options import LinkStyle

options = MarkdownOptions(link_style=LinkStyle.REFERENCE)
result = MarkdownGenerator(options).generate_from_html(html)
```

## Асинхронний виклик

```python
import asyncio
from markdown import generate_markdown_async

async def run():
    result = await generate_markdown_async(html)
    print(result.fit_markdown)

asyncio.run(run())
```

## Витяг дат публікації

```python
from markdown import MarkdownGenerator, MarkdownOptions

options = MarkdownOptions(extract_dates=True)  # потрібен пакет htmldate
result = MarkdownGenerator(options).generate_from_html(html)
print(result.published_date, result.updated_date)
```

## Фасад під web-scraping

```python
from main_service import HTMLToMarkdownConverter

converter = HTMLToMarkdownConverter()  # агресивніші дефолти під scraping
markdown = converter.convert(html)
```
