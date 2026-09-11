"""Опції конвертації HTML у Markdown.

Єдине джерело правди для дефолтів. Значення підбираються під web-scraping;
Pydantic-валідатор ловить опечатки в enum-полях і в regex-патернах.
"""

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LinkStyle(StrEnum):
    """Стиль рендеру посилань: inline ``[text](url)`` або reference ``[text][N]``."""

    INLINE = "inline"
    REFERENCE = "reference"


class NewlineStyle(StrEnum):
    """Стиль hard-break для ``<br>``: два пробіли або зворотний слеш."""

    SPACES = "spaces"
    BACKSLASH = "backslash"


class MarkdownOptions(BaseModel):
    """Опції для ``MarkdownGenerator`` (immutable-style: використовуй ``with_overrides``).

    Приклад:
        options = MarkdownOptions(remove_footer=True, include_links=False, max_length=50000)
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
    )

    # Видалення noise елементів
    remove_nav: bool = Field(default=True, description="Видаляти nav елементи")
    remove_header: bool = Field(default=True, description="Видаляти header елементи")
    remove_footer: bool = Field(default=True, description="Видаляти footer елементи")
    remove_aside: bool = Field(default=True, description="Видаляти aside елементи")
    remove_ads: bool = Field(default=True, description="Видаляти рекламу за класами/id")
    remove_scripts: bool = Field(default=True, description="Видаляти script, style, noscript")
    remove_buttons: bool = Field(default=True, description="Видаляти button елементи")
    remove_forms: bool = Field(default=False, description="Видаляти form елементи")
    remove_hidden: bool = Field(default=True, description="Видаляти приховані елементи (aria-hidden, HTML5 hidden, hidden-класи)")
    remove_display_none: bool = Field(
        default=False,
        description="Видаляти елементи з inline style=\"display:none\" (ризик false-positive на невалідних стилях)",
    )

    # Теги для видалення (immutable для thread-safety)
    noise_tags: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "script",
                "style",
                "noscript",
                "template",
                "svg",
                "canvas",
                "iframe",
                "embed",
                "object",
                "video",
                "audio",
                "select",
                "option",
                "optgroup",
            }
        ),
        description="Теги для автоматичного видалення",
    )

    # Класи для видалення (реклама, попапи)
    noise_classes: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "ad",
                "ads",
                "advertisement",
                "advert",
                "banner",
                "sidebar",
                "cookie",
                "popup",
                "modal",
                "overlay",
                "newsletter",
                "subscribe",
                "social",
                "share",
                "comment",
                "comments",
                "related",
                "recommended",
            }
        ),
        description="CSS класи для видалення",
    )

    # ID для видалення
    noise_ids: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "cookie",
                "popup",
                "modal",
                "overlay",
                "ad",
                "ads",
                "sidebar",
                "newsletter",
                "comments",
            }
        ),
        description="HTML ID для видалення",
    )

    # Включення контенту
    include_links: bool = Field(default=True, description="Включати посилання в MD")
    include_images: bool = Field(default=False, description="Включати зображення в MD")
    include_tables: bool = Field(default=True, description="Включати таблиці в MD")
    include_code_blocks: bool = Field(default=True, description="Включати код в MD")
    include_lists: bool = Field(default=True, description="Включати списки в MD")
    include_blockquotes: bool = Field(default=True, description="Включати цитати в MD")

    # Обмеження
    max_length: int = Field(default=100000, ge=0, description="Максимальна довжина тексту")
    min_paragraph_length: int = Field(default=3, ge=0, description="Мінімальна довжина параграфа")
    min_heading_length: int = Field(default=1, ge=0, description="Мінімальна довжина заголовка")
    max_word_length: int = Field(default=80, ge=0, description="Максимальна довжина слова; довші слова (CSS/class-name garbage) видаляються")

    # Форматування
    preserve_whitespace: bool = Field(default=False, description="Зберігати whitespace")
    normalize_whitespace: bool = Field(default=True, description="Нормалізувати пробіли")

    # Citations
    generate_citations: bool = Field(default=False, description="Генерувати [1], [2] посилання")

    # URL нормалізація
    base_url: str = Field(default="", description="Базовий URL для конвертації відносних URL")
    normalize_urls: bool = Field(default=True, description="Конвертувати відносні URL в абсолютні")

    # Опційне очищення URL через courlan: прибирає UTM/tracker-параметри
    # (utm_*, fbclid, gclid). Працює разом з normalize_urls + base_url.
    clean_urls: bool = Field(
        default=False,
        description=(
            "Якщо True — посилання/зображення проходять через courlan.clean_url "
            "(видаляє UTM/tracker-хвости)."
        ),
    )

    # Контекстна фільтрація
    use_content_density: bool = Field(
        default=False,
        description="Використовувати аналіз щільності тексту для визначення основного контенту",
    )

    # Link-density + content-density fallback
    link_density_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "Кандидати main-content з link_density > threshold (меню/футер) "
            "виключаються. link_density = link_chars / total_chars."
        ),
    )

    min_content_words: int = Field(
        default=100,
        ge=0,
        description=(
            "Мінімальна кількість слів у extracted main content. Якщо "
            "content-density extractor видав менше слів — fallback на "
            "повний root (гарантує recall на коротких сторінках)."
        ),
    )

    # Тюнінг `_find_main_content`.
    main_content_min_length: int = Field(
        default=200,
        ge=0,
        description=(
            "Мінімальна довжина тексту кандидата у main-content extractor. "
            "Кандидати з text_length < цього значення відкидаються. "
            "Для e-commerce / коротких карток контенту зменшуй до 80–120."
        ),
    )
    main_content_semantic_bonus: float = Field(
        default=1.5,
        ge=0.0,
        description=(
            "Множник score для семантичних тегів (`<article>`, `<main>`) "
            "у main-content extractor."
        ),
    )
    main_content_noise_penalty: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description=(
            "Множник score для елементів з noise-класами/id у main-content "
            "extractor. 0.0 → повне виключення, 1.0 → без штрафу."
        ),
    )

    # Selectolax-парсер за замовчуванням; форс BeautifulSoup — fallback.
    force_beautifulsoup: bool = Field(
        default=False, description="Примусово використовувати BeautifulSoup замість selectolax"
    )

    # Regex-патерни для видалення шумових фрагментів з тексту (dynamic noise).
    dynamic_noise_patterns: list[str] = Field(
        default_factory=list, description="Regex патерни для видалення з тексту"
    )

    @field_validator("dynamic_noise_patterns")
    @classmethod
    def _validate_dynamic_noise_patterns(cls, patterns: list[str]) -> list[str]:
        """Відхиляє невалідні regex одразу з ``ValueError`` замість тихого warning."""
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(
                    f"Invalid regex pattern in dynamic_noise_patterns: {pattern!r} ({e})"
                ) from e
        return patterns

    def get_combined_noise_re(self):
        """Повертає прекомпільований union-regex усіх ``dynamic_noise_patterns``.

        Використовує модульний кеш ``_COMBINED_NOISE_CACHE`` (ключ — tuple patterns).
        Leading global-inline flags (``(?i)``, ``(?s)`` тощо) конвертуються у
        локальні ``(?i:...)``, бо у Python global-flags валідні лише на початку
        всього regex і при простій альтернації ламаються.
        """
        if not self.dynamic_noise_patterns:
            return None
        key = tuple(self.dynamic_noise_patterns)
        cached = _COMBINED_NOISE_CACHE.get(key)
        if cached is not None:
            return cached
        parts = [_wrap_pattern_with_local_flags(p) for p in self.dynamic_noise_patterns]
        joined = "|".join(parts)
        compiled = re.compile(joined)
        _COMBINED_NOISE_CACHE[key] = compiled
        return compiled

    # Витяг inline-тексту з div/section, коли <p> відсутні.
    extract_div_text: bool = Field(
        default=True, description="Витягувати текст з div/section без <p> тегів"
    )

    preserve_inline_formatting: bool = Field(
        default=True, description="Зберігати inline форматування (strong, em, code)"
    )

    # Bullet cycling + newline style
    bullets: str = Field(
        default="-",
        description=(
            "Символи bullet'ів по рівнях вкладеності (наприклад '-*+' "
            "→ перший рівень '-', другий '*', третій '+'). Перемикання "
            "по depth % len(bullets)."
        ),
    )

    newline_style: NewlineStyle = Field(
        default=NewlineStyle.SPACES,
        description=(
            "Стиль hard-break для <br>: 'spaces' → '  \\n' (CommonMark), "
            "'backslash' → '\\\\\\n' (GFM-friendly)."
        ),
    )

    # Context-sensitive escaping
    strict_escape: bool = Field(
        default=False,
        description=(
            "Якщо True — renderer екранує всі CommonMark-спецсимволи "
            "(`*_{}[]()#+-!) у Text-вузлах. За замовчуванням False: raw "
            "Text-вузли вже містять готову розмітку, повторне екранування ламає рендер."
        ),
    )

    # Reference-style links
    link_style: LinkStyle = Field(
        default=LinkStyle.INLINE,
        description=(
            "Стиль посилань: 'inline' → [text](url), "
            "'reference' → [text][N] + внизу [N]: url. "
            "Reference-style зменшує шум у довгих статтях (CommonMark/GFM)."
        ),
    )

    use_trafilatura_extraction: bool = Field(
        default=False,
        description=(
            "Якщо True — HTML спочатку проходить через trafilatura.extract() "
            "для витягування основного контенту (boilerplate removal), і лише "
            "потім подається у конвертер."
        ),
    )

    # Опційна NFKC-нормалізація Unicode: fullwidth → ASCII, лігатури тощо.
    normalize_unicode: bool = Field(
        default=False,
        description="Якщо True — text/fit_markdown проходять через unicodedata.normalize('NFKC', ...).",
    )

    # Опційне лікування mojibake через ftfy (опційна залежність).
    fix_text_encoding: bool = Field(
        default=False,
        description="Якщо True — HTML проганяється через ftfy.fix_text() перед парсингом.",
    )

    # Опційний витяг дат публікації/оновлення через htmldate (опційна залежність).
    extract_dates: bool = Field(
        default=False,
        description=(
            "Якщо True — з HTML витягуються published_date/updated_date через "
            "htmldate.find_date() і кладуться у MarkdownResult."
        ),
    )
    extract_dates_extensive: bool = Field(
        default=False,
        description=(
            "extensive_search для htmldate. Default False: повний режим "
            "додає ~200 ms/документ. Діє лише разом з extract_dates=True."
        ),
    )
    date_output_format: str = Field(
        default="%Y-%m-%d",
        description="strftime-формат для published_date/updated_date (htmldate outputformat).",
    )

    # Опційна санітизація HTML через nh3 (Rust/ammonia) перед конвертацією.
    sanitize_html: bool = Field(
        default=False,
        description=(
            "Якщо True — HTML проганяється через nh3.clean() перед парсингом "
            "(вирізає script/style/on*-handlers, javascript:-URL). "
            "Актуально для user-generated content."
        ),
    )

    def should_remove_tag(self, tag_name: str) -> bool:
        """Перевіряє чи потрібно видалити тег."""
        tag_lower = tag_name.lower()

        # Завжди видаляємо noise теги
        if tag_lower in self.noise_tags:
            return True

        # Перевіряємо опціональні теги
        if self.remove_nav and tag_lower == "nav":
            return True
        if self.remove_header and tag_lower == "header":
            return True
        if self.remove_footer and tag_lower == "footer":
            return True
        if self.remove_aside and tag_lower == "aside":
            return True
        if self.remove_buttons and tag_lower == "button":
            return True
        if self.remove_forms and tag_lower == "form":
            return True

        return False

    def should_remove_by_class(self, class_str: str) -> bool:
        """Перевіряє чи потрібно видалити елемент за класом."""
        if not class_str or not self.remove_ads:
            return False

        # Розбиваємо на окремі класи та перевіряємо як повні слова
        class_set = set(class_str.lower().split())
        return bool(class_set & self.noise_classes)

    def should_remove_by_id(self, id_str: str) -> bool:
        """Перевіряє чи потрібно видалити елемент за ID (substring match)."""
        if not id_str or not self.remove_ads:
            return False

        id_lower = id_str.lower()
        return any(ni in id_lower for ni in self.noise_ids)

    def should_remove_hidden(self, attrs: dict) -> bool:
        """Перевіряє чи потрібно видалити елемент з aria-hidden=\"true\"."""
        if not self.remove_hidden:
            return False
        return attrs.get("aria-hidden", "").lower() == "true"

    def with_overrides(self, **kwargs) -> "MarkdownOptions":
        """Повертає нову копію опцій з переписаними значеннями (immutable pattern)."""
        data = self.model_dump()
        data.update(kwargs)
        return MarkdownOptions(**data)


# CSS-класи, що загальноприйнято ховають елемент візуально.
HIDDEN_CSS_CLASSES = frozenset({"d-none", "sr-only", "visually-hidden", "hidden"})


# Модульний кеш union-regex для `dynamic_noise_patterns` (ключ — tuple patterns).
_COMBINED_NOISE_CACHE: dict[tuple, "re.Pattern"] = {}


# Leading global-inline flags: `(?i)`, `(?im)`, `(?ims)`, etc.
_LEADING_GLOBAL_FLAGS_RE = re.compile(r"^\(\?([aiLmsux]+)\)")


def _wrap_pattern_with_local_flags(pattern: str) -> str:
    """Огортає pattern у ``(?:...)``, конвертуючи leading global-flags у локальні.

    У Python global inline-flags валідні лише на початку всього regex. При
    простій альтернації локальні flag-групи ``(?i:...)`` працюють у будь-якій
    позиції.
    """
    m = _LEADING_GLOBAL_FLAGS_RE.match(pattern)
    if m:
        flags = m.group(1)
        body = pattern[m.end():]
        return f"(?{flags}:{body})"
    return f"(?:{pattern})"


# Дві множини noise-класів різної агресивності.
# SAFE_NOISE_CLASSES: майже нульовий ризик false-positive (реклама, попапи,
# соціальні шар'ери, cookie-banner тощо). Використовуй як дефолт.
SAFE_NOISE_CLASSES = frozenset({
    "ad", "ads", "advertisement", "advert", "banner",
    "cookie", "popup", "modal", "overlay",
    "newsletter", "subscribe", "social", "share",
    "sponsored", "promo", "disclaimer",
})

# AGGRESSIVE_NOISE_CLASSES: додатково зрізає sidebar/related/recommended/
# comments — вони часто виносять корисний контент, тому вмикай свідомо.
AGGRESSIVE_NOISE_CLASSES = SAFE_NOISE_CLASSES | frozenset({
    "sidebar", "related", "recommended", "comment", "comments",
    "carousel",
})


# Типовий набір шумових regex-патернів (timestamps, лічильники, CTA-кнопки, job-ID)
# для встановлення у `MarkdownOptions.dynamic_noise_patterns`.
COMMON_NOISE_PATTERNS = [
    # Timestamps
    r"(?i)(posted|published|listed|updated)\s+\d+\s+(days?|hours?|weeks?|months?)\s+ago",
    r"(?i)\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}",
    # Counters
    r"(?i)\d+\s*(applicants?|views?|people\s+applied)",
    # CTA buttons text
    r"(?i)(apply\s+now|save\s+job|share\s+this|sign\s+in\s+to)",
    r"(?i)(easy\s+apply|quick\s+apply|one[\s-]click)",
    # Job IDs
    r"(?i)job\s*(id|ref|reference)\s*[:#]?\s*[\w\-]+",
]
