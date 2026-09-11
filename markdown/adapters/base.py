"""Базова абстракція для HTML адаптерів.

Визначає інтерфейс для роботи з різними HTML парсерами через уніфікований API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class HTMLElement:
    """Уніфікований wrapper для HTML-елемента.

    Обгортає елементи різних парсерів (BeautifulSoup, Selectolax) в єдиний
    інтерфейс. Делегує реальні операції до ``adapter``.
    """

    __slots__ = ("tag_name", "native", "adapter")

    tag_name: str
    native: Any
    adapter: BaseHTMLAdapter

    def get_text(self, strip: bool = True, separator: str = " ") -> str:
        return self.adapter.get_text(self.native, strip=strip, separator=separator)

    def get_attribute(self, name: str, default: str = "") -> str:
        return self.adapter.get_attribute(self.native, name, default)

    def find_children(self, tag_names: list[str] | None = None, recursive: bool = True) -> list[HTMLElement]:
        return self.adapter.find_children(self.native, tag_names, recursive)

    def has_children(self, tag_names: list[str]) -> bool:
        """True, якщо є хоча б один прямий дочірній елемент з переліку тегів."""
        return len(self.find_children(tag_names, recursive=False)) > 0

    def get_html(self) -> str:
        return self.adapter.get_html(self.native)

    def iter_descendants(self) -> Iterator[HTMLElement]:
        """Ітерує по всіх нащадках у порядку появи в DOM."""
        return self.adapter.iter_descendants(self.native)

    def iter_direct_children_mixed(self) -> Iterator[tuple[str, Any]]:
        """Прямі діти елемента, включно з текстовими вузлами.

        Yields:
            tuple[kind, value] — див. ``BaseHTMLAdapter.iter_direct_children_mixed``.
        """
        return self.adapter.iter_direct_children_mixed(self.native)

    @property
    def native_id(self) -> int:
        """Стабільний ідентифікатор DOM-вузла.

        Працює коректно, коли парсер створює нові Python-обгортки для того
        самого C-вузла при кожному обході (BS4 → ``id()``, Selectolax → ``mem_id``).
        """
        return self.adapter.get_native_id(self.native)


class BaseHTMLAdapter(ABC):
    """Уніфікований інтерфейс до HTML-парсера.

    Приклад:
        adapter = BeautifulSoupAdapter(soup)
        root = adapter.get_root()
        for child in root.iter_descendants():
            ...
    """

    @abstractmethod
    def get_root(self) -> HTMLElement:
        """Кореневий елемент документа (зазвичай ``<body>``)."""

    @abstractmethod
    def get_tag_name(self, element: Any) -> str:
        """Назва тегу елемента в нижньому регістрі."""

    @abstractmethod
    def get_text(self, element: Any, strip: bool = True, separator: str = " ") -> str:
        """Текстовий контент елемента."""

    @abstractmethod
    def get_attribute(self, element: Any, name: str, default: str = "") -> str:
        """Значення атрибута або ``default``."""

    @abstractmethod
    def find_children(
            self, element: Any, tag_names: list[str] | None = None, recursive: bool = True
    ) -> list[HTMLElement]:
        """Дочірні елементи (опціонально фільтровані по тегах, рекурсивно чи ні)."""

    @abstractmethod
    def iter_descendants(self, element: Any) -> Iterator[HTMLElement]:
        """Ітерація по всіх нащадках у порядку DOM."""

    @abstractmethod
    def get_html(self, element: Any) -> str:
        """HTML-представлення елемента."""

    @abstractmethod
    def find_all(self, tag_names: list[str]) -> list[HTMLElement]:
        """Усі елементи документа з переліку тегів."""

    @abstractmethod
    def iter_direct_children_mixed(self, element: Any) -> Iterator[tuple[str, Any]]:
        """Прямі діти елемента, включаючи текстові вузли.

        Потрібно для обробки mixed content (текст + inline + block у одному
        контейнері — типовий патерн bootstrap-карток).

        Yields:
            tuple[kind, value] де
              - ``kind == 'text'``    → value: ``str`` (текстовий сегмент; коментарі пропускаються);
              - ``kind == 'element'`` → value: ``HTMLElement`` (тег-нащадок 1-го рівня).
        """

    def get_native_id(self, element: Any) -> int:
        """Стабільний ідентифікатор нативного DOM-вузла.

        Дефолт — ``id()`` (валідно для BS4). Адаптери, що створюють нові
        Python-обгортки при кожному обході (Selectolax), перевизначають метод.
        """
        return id(element)

    def wrap_element(self, native_element: Any) -> HTMLElement:
        """Обгортає нативний вузол у ``HTMLElement``."""
        tag_name = self.get_tag_name(native_element)
        return HTMLElement(tag_name=tag_name, native=native_element, adapter=self)
