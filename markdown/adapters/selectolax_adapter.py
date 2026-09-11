"""Selectolax адаптер для уніфікованої роботи з HTML.

Обгортає Selectolax API в BaseHTMLAdapter інтерфейс.
"""

from __future__ import annotations

from typing import Any, Iterator

from markdown.adapters.base import BaseHTMLAdapter, HTMLElement


class SelectolaxAdapter(BaseHTMLAdapter):
    """Адаптер ``BaseHTMLAdapter`` над Selectolax (швидкий Cython-парсер)."""

    def __init__(self, tree: Any):
        self.tree = tree

    def get_root(self) -> HTMLElement:
        root = self.tree.css_first("body") or self.tree.root
        return self.wrap_element(root)

    def get_tag_name(self, element: Any) -> str:
        if hasattr(element, "tag") and element.tag:
            return element.tag.lower()
        return ""

    def get_text(self, element: Any, strip: bool = True, separator: str = " ") -> str:
        """Текст елемента (Selectolax ігнорує ``separator``)."""
        if not hasattr(element, "text"):
            return ""

        # Selectolax text() method приймає strip як параметр
        try:
            return element.text(strip=strip)
        except TypeError:
            # Якщо версія не підтримує strip parameter
            text = element.text()
            return text.strip() if strip and text else text or ""

    def get_attribute(self, element: Any, name: str, default: str = "") -> str:
        if not hasattr(element, "attributes"):
            return default

        attrs = element.attributes or {}
        value = attrs.get(name, default)

        return str(value) if value else default

    def find_children(self, element: Any, tag_names: list[str] | None = None, recursive: bool = True) -> list[HTMLElement]:
        """Знаходить дочірні елементи через Selectolax.

        Selectolax ``node.iter()`` дає прямих дітей, ``node.css('*')`` —
        усіх нащадків. Порівнювати ``child.parent == element`` не можна:
        ``__eq__`` у Selectolax порівнює структуру.
        """
        if not recursive:
            # Прямі діти через iter()
            if not hasattr(element, "iter"):
                return []
            try:
                direct = [c for c in element.iter() if hasattr(c, "tag") and c.tag]
            except (AttributeError, ValueError):
                return []

            if tag_names:
                tag_set = {t.lower() for t in tag_names}
                direct = [c for c in direct if c.tag.lower() in tag_set]

            return [self.wrap_element(el) for el in direct]

        # recursive=True
        if not hasattr(element, "css"):
            return []

        if not tag_names:
            try:
                found = list(element.css("*"))
            except (AttributeError, ValueError):
                return []
            return [self.wrap_element(el) for el in found if hasattr(el, "tag") and el.tag]

        selector = ", ".join(tag_names)
        try:
            found = element.css(selector)
            return [self.wrap_element(el) for el in found if hasattr(el, "tag") and el.tag]
        except (AttributeError, ValueError):
            return []

    def iter_descendants(self, element: Any) -> Iterator[HTMLElement]:
        if not hasattr(element, "css"):
            return

        try:
            # css('*') повертає ВСІХ нащадків у порядку DOM.
            for descendant in element.css("*"):
                if hasattr(descendant, "tag") and descendant.tag:
                    yield self.wrap_element(descendant)
        except (AttributeError, ValueError):
            return

    def get_html(self, element: Any) -> str:
        if not hasattr(element, "html"):
            return ""

        try:
            html = element.html
            return html if html else ""
        except (AttributeError, TypeError):
            return ""

    def find_all(self, tag_names: list[str]) -> list[HTMLElement]:
        if not hasattr(self.tree, "css"):
            return []

        selector = ", ".join(tag_names)

        try:
            found = self.tree.css(selector)
            return [self.wrap_element(el) for el in found if hasattr(el, "tag")]
        except (AttributeError, ValueError):
            return []

    def iter_direct_children_mixed(self, element: Any) -> Iterator[tuple[str, Any]]:
        """Прямі діти Selectolax-вузла, включаючи текстові ноди.

        Selectolax повертає текстові вузли як ``Node`` з ``tag == '-text'``.
        Ми перетворюємо їх у ``('text', str)``. Інші вузли — ``('element',
        HTMLElement)``. Коментарі (``--comment``) пропускаються.
        """
        if not hasattr(element, "iter"):
            return

        try:
            children = element.iter(include_text=True)
        except TypeError:
            # Дуже старі версії selectolax без include_text — fallback на
            # лише елементи, без text-нод (mixed-content не обробиться,
            # але runtime не падає).
            children = element.iter()

        for child in children:
            tag = getattr(child, "tag", None)
            if not tag:
                continue

            if tag == "-text":
                # Selectolax: текстовий вміст беремо через text(deep=False).
                try:
                    raw = child.text(deep=False, strip=False) or ""
                except TypeError:
                    raw = child.text() or ""
                if raw:
                    yield ("text", raw)
                continue

            # Коментарі/CDATA пропускаємо.
            if tag.startswith("-") or tag.startswith("!"):
                continue

            yield ("element", self.wrap_element(child))

    def get_native_id(self, element: Any) -> int:
        """Стабільний ID Selectolax-вузла.

        Selectolax створює нові Python-обгортки при кожному обході
        (``iter``/``css``), тож ``id(element)`` нестабільний. Натомість
        використовуємо ``mem_id`` — адресу C-вузла, однакову для всіх
        обгорток одного DOM-елемента.
        """
        mem_id = getattr(element, "mem_id", None)
        if mem_id is not None:
            return mem_id
        return id(element)
