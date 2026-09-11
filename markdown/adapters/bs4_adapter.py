"""BeautifulSoup адаптер для уніфікованої роботи з HTML.

Обгортає BeautifulSoup API в BaseHTMLAdapter інтерфейс.
"""

from __future__ import annotations

from typing import Any, Iterator

from markdown.adapters.base import BaseHTMLAdapter, HTMLElement


class BeautifulSoupAdapter(BaseHTMLAdapter):
    """Адаптер ``BaseHTMLAdapter`` над BeautifulSoup."""

    def __init__(self, soup: Any):
        self.soup = soup

    def get_root(self) -> HTMLElement:
        root = self.soup.find("body") or self.soup
        return self.wrap_element(root)

    def get_tag_name(self, element: Any) -> str:
        if hasattr(element, "name") and element.name:
            return element.name.lower()
        return ""

    def get_text(self, element: Any, strip: bool = True, separator: str = " ") -> str:
        if not hasattr(element, "get_text"):
            return ""
        return element.get_text(strip=strip, separator=separator)

    def get_attribute(self, element: Any, name: str, default: str = "") -> str:
        if not hasattr(element, "get"):
            return default

        value = element.get(name, default)

        # BS4 може повертати list для class та інших multi-value атрибутів
        if isinstance(value, list):
            return " ".join(value)

        return str(value) if value else default

    def find_children(self, element: Any, tag_names: list[str] | None = None, recursive: bool = True) -> list[HTMLElement]:
        if not hasattr(element, "find_all"):
            return []

        # BeautifulSoup приймає list тегів або True для всіх
        search_tags = tag_names if tag_names else True

        found = element.find_all(search_tags, recursive=recursive)
        return [self.wrap_element(el) for el in found if hasattr(el, "name")]

    def iter_descendants(self, element: Any) -> Iterator[HTMLElement]:
        if not hasattr(element, "descendants"):
            return

        for descendant in element.descendants:
            # Фільтруємо тільки Tag об'єкти (не NavigableString)
            if hasattr(descendant, "name") and descendant.name:
                yield self.wrap_element(descendant)

    def get_html(self, element: Any) -> str:
        if not hasattr(element, "decode"):
            return ""

        # decode() в BS4 конвертує Tag назад в HTML string
        try:
            return element.decode()
        except (AttributeError, TypeError):
            return str(element)

    def find_all(self, tag_names: list[str]) -> list[HTMLElement]:
        if not hasattr(self.soup, "find_all"):
            return []

        found = self.soup.find_all(tag_names)
        return [self.wrap_element(el) for el in found if hasattr(el, "name")]

    def iter_direct_children_mixed(self, element: Any) -> Iterator[tuple[str, Any]]:
        """Прямі діти елемента (Tag + NavigableString), без коментарів.

        BS4 ``Tag.children`` віддає і ``Tag``, і ``NavigableString``. Ми
        фільтруємо ``Comment`` (підклас ``NavigableString``), щоб у вивід
        не потрапляла HTML-коментарна служба.
        """
        # Lazy import — не тягнемо bs4 у адаптер на module level.
        try:
            from bs4 import Comment, NavigableString
        except ImportError:
            Comment = None  # type: ignore[assignment]
            NavigableString = None  # type: ignore[assignment]

        if not hasattr(element, "children"):
            return

        for child in element.children:
            # NavigableString (включно з Comment, CData, Doctype) — текст.
            if NavigableString is not None and isinstance(child, NavigableString):
                if Comment is not None and isinstance(child, Comment):
                    continue
                yield ("text", str(child))
                continue

            # Tag — обгортаємо в HTMLElement.
            if hasattr(child, "name") and child.name:
                yield ("element", self.wrap_element(child))
