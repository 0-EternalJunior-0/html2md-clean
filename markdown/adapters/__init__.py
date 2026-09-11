"""HTML Adapters для уніфікованої конвертації в Markdown.

Цей модуль надає абстракцію над різними HTML парсерами (BeautifulSoup, Selectolax, lxml)
через Adapter Pattern, що дозволяє використовувати один алгоритм конвертації.
"""

from markdown.adapters.base import BaseHTMLAdapter, HTMLElement
from markdown.adapters.bs4_adapter import BeautifulSoupAdapter
from markdown.adapters.selectolax_adapter import SelectolaxAdapter

__all__ = [
    "BaseHTMLAdapter",
    "HTMLElement",
    "BeautifulSoupAdapter",
    "SelectolaxAdapter",
]
