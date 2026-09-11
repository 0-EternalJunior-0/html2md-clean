import time
import tracemalloc

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions


def test_2m_html_stress():
    # 2 000 000 символів тексту
    text = "Lorem ipsum dolor sit amet. " * 70_000

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stress test</title>
    </head>
    <body>
        <article>
            <h1>Large document</h1>
            <p>{text}</p>
        </article>
    </body>
    </html>
    """

    print(f"\nInput HTML: {len(html):,} chars")
    print(f"Input HTML: {len(html.encode('utf-8')) / 1024 / 1024:.2f} MB")

    options = MarkdownOptions(
        max_length=200_000,
    )

    generator = MarkdownGenerator(options)

    tracemalloc.start()
    start = time.perf_counter()

    result = generator.generate_from_html(html)

    elapsed = time.perf_counter() - start

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"Output Markdown: {len(result.fit_markdown):,} chars")
    print(f"Time: {elapsed:.3f} sec")
    print(f"Peak Python memory: {peak / 1024 / 1024:.2f} MB")

    assert result.fit_markdown