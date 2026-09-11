"""Модель результату генерації Markdown."""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

if TYPE_CHECKING:
    from markdown.generator import MarkdownGenerator


class MarkdownResult(BaseModel):
    """Результат генерації Markdown із варіантами тексту та статистикою.

    Поля:
        text: чистий текст без форматування.
        fit_markdown: основний очищений Markdown.
        raw_markdown: повний Markdown, генерується лениво при першому доступі.
        markdown_with_citations: варіант з посиланнями ``[1]``, ``[2]``.

    Приклад:
        result = generator.generate_from_html(html)
        print(result.fit_markdown)
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
    )

    text: str = Field(default="", description="Чистий текст без форматування")
    fit_markdown: str = Field(default="", description="Очищений Markdown (основний output)")

    _raw_markdown: str | None = PrivateAttr(default=None)
    _raw_html: str | None = PrivateAttr(default=None)
    _raw_tree: Any = PrivateAttr(default=None)
    _generator_ref: Any = PrivateAttr(default=None)

    markdown_with_citations: str = Field(default="", description="Markdown з [1], [2] посиланнями")
    references: list[dict[str, Any]] = Field(default_factory=list, description="Список посилань")

    title: str = Field(default="", description="Title сторінки")
    h1: str = Field(default="", description="Перший H1 заголовок")
    description: str = Field(default="", description="Meta description")

    word_count: int = Field(default=0, ge=0, description="Кількість слів")
    char_count: int = Field(default=0, ge=0, description="Кількість символів")
    heading_count: int = Field(default=0, ge=0, description="Кількість заголовків")
    link_count: int = Field(default=0, ge=0, description="Кількість посилань")
    rendered_link_count: int = Field(default=0, ge=0, description="Кількість посилань, вставлених у markdown")
    image_count: int = Field(default=0, ge=0, description="Кількість зображень")

    is_truncated: bool = Field(default=False, description="Чи був обрізаний текст")

    published_date: str | None = Field(
        default=None,
        description="Дата публікації (htmldate, opt-in через MarkdownOptions.extract_dates)",
    )
    updated_date: str | None = Field(
        default=None,
        description="Дата останнього оновлення (htmldate, opt-in через MarkdownOptions.extract_dates)",
    )

    def model_post_init(self, __context) -> None:
        if self.text and not self.word_count:
            object.__setattr__(self, "word_count", len(self.text.split()))
        if self.text and not self.char_count:
            object.__setattr__(self, "char_count", len(self.text))

    @property
    def raw_markdown(self) -> str:
        """Ленива генерація повного Markdown з попередньо збереженого дерева або HTML."""
        if self._raw_markdown is None:
            if self._raw_tree is not None and self._generator_ref:
                self._raw_markdown = self._generator_ref._generate_raw_markdown_from_tree(
                    self._raw_tree
                )
            elif self._raw_html and self._generator_ref:
                self._raw_markdown = self._generator_ref._generate_raw_markdown(self._raw_html)
            else:
                self._raw_markdown = ""
        return self._raw_markdown

    @raw_markdown.setter
    def raw_markdown(self, value: str) -> None:
        self._raw_markdown = value

    @property
    def markdown(self) -> str:
        """Аліас для ``fit_markdown``."""
        return self.fit_markdown

    def set_lazy_raw_markdown(self, raw_html: str, generator: "MarkdownGenerator") -> None:
        """Зберігає HTML-рядок для лінивої генерації ``raw_markdown``."""
        self._raw_html = raw_html
        self._generator_ref = generator

    def set_lazy_raw_tree(self, tree: Any, generator: "MarkdownGenerator") -> None:
        """Зберігає клон дерева для лінивої генерації ``raw_markdown`` без повторного парсингу."""
        self._raw_tree = tree
        self._generator_ref = generator

    def to_dict(self) -> dict:
        data = self.model_dump()
        data["raw_markdown"] = self.raw_markdown
        return data

    @classmethod
    def empty(cls) -> "MarkdownResult":
        return cls()

    def __bool__(self) -> bool:
        return bool(self.text or self.fit_markdown)

    def __repr__(self) -> str:
        return f"MarkdownResult(words={self.word_count}, chars={self.char_count}, truncated={self.is_truncated})"
