"""Публічний API пакета генерації Markdown з HTML.

Точка входу: `MarkdownGenerator`. Підтримує BeautifulSoup та Selectolax.

Приклад:
    from markdown import MarkdownGenerator, MarkdownOptions

    md = MarkdownGenerator()
    result = md.generate_from_html(html)
"""

import logging as _logging

from markdown.generator import (
    MarkdownGenerator,
    generate_markdown_async,
)
from markdown.logging_config import configure_logging
from markdown.options import (
    COMMON_NOISE_PATTERNS,
    MarkdownOptions,
)
from markdown.result import MarkdownResult

_logging.getLogger("markdown").addHandler(_logging.NullHandler())

__all__ = [
    "MarkdownGenerator",
    "MarkdownOptions",
    "MarkdownResult",
    "generate_markdown_async",
    "COMMON_NOISE_PATTERNS",
    "configure_logging",
]
