"""Уніфікований Markdown конвертер.

Єдиний алгоритм конвертації HTML → Markdown що працює з будь-яким
адаптером (BeautifulSoup, Selectolax, lxml) через BaseHTMLAdapter інтерфейс.
"""

from __future__ import annotations

import html
import re
from typing import TypedDict
from urllib.parse import urljoin

from bs4 import Comment, NavigableString, Tag

from markdown.adapters.base import BaseHTMLAdapter, HTMLElement
from markdown.options import MarkdownOptions


class ConvertStats(TypedDict):
    """Статистика конвертації, повертається з `UnifiedMarkdownConverter.convert`.

    Типізований словник: IDE/mypy ловлять опечатки в ключах.
    """

    headings: int
    links: int
    images: int
    code: int
    lists: int
    tables: int
    rendered_links: int


# Precompiled regex patterns for performance
_RE_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RE_CODE = re.compile(r"<code[^>]*>(.*?)</code>", re.IGNORECASE | re.DOTALL)
_RE_STRONG = re.compile(r"<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>", re.IGNORECASE | re.DOTALL)
_RE_EM = re.compile(r"<(?:em|i)[^>]*>(.*?)</(?:em|i)>", re.IGNORECASE | re.DOTALL)
_RE_DEL = re.compile(r"<(?:del|s|strike)[^>]*>(.*?)</(?:del|s|strike)>", re.IGNORECASE | re.DOTALL)
_RE_LINK = re.compile(r"<a\s+([^>]*?)>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_RE_LINK_STRIP = re.compile(r"<a[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_RE_HREF = re.compile(r'href=["\']([^"\']+)["\']')
_RE_TAG_STRIP = re.compile(r"<[^>]+>")
_RE_HARDBREAK_SPACES = re.compile(r" {2,}\n")
_RE_HARDBREAK_BACKSLASH = re.compile(r"\\\n")
_RE_SPACES = re.compile(r" +")
_RE_TABS = re.compile(r"[ \t]+")
_RE_NEWLINES = re.compile(r"\n{3,}")
_RE_NL_TRIM = re.compile(r" *\n *")
_RE_TAG_PARSE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9]*)\b[^>]*?>", re.IGNORECASE)
_RE_LONG_WORD = re.compile(r"\S{80,}")


class UnifiedMarkdownConverter:
    """Уніфікований конвертер HTML → Markdown поверх ``BaseHTMLAdapter``.

    Приклад:
        converter = UnifiedMarkdownConverter(options)
        markdown, stats = converter.convert(adapter)
    """

    def __init__(self, options: MarkdownOptions):
        self.options = options
        self._link_refs: list[dict[str, str]] = []
        self._ref_counter = 0
        self._rendered_links = 0

    def convert(self, adapter: BaseHTMLAdapter) -> tuple[str, ConvertStats]:
        """Конвертує HTML у Markdown, повертає ``(markdown, ConvertStats)``."""
        self._link_refs = []
        self._ref_counter = 0
        self._rendered_links = 0

        root = adapter.get_root()

        use_density = (
                hasattr(self.options, "use_content_density") and self.options.use_content_density
        )

        if use_density:
            main_root = self._find_main_content(adapter, root)
            markdown, stats = self._convert_subtree(main_root)

            # Fallback chain: якщо main-content занадто короткий, повторюємо
            # на повному root (Trafilatura-style recall).
            min_words = getattr(self.options, "min_content_words", 100)
            if min_words > 0 and main_root is not root:
                word_count = len(markdown.split())
                if word_count < min_words:
                    markdown, stats = self._convert_subtree(root)
            return markdown, stats

        return self._convert_subtree(root)

    def _convert_subtree(self, root: HTMLElement) -> tuple[str, ConvertStats]:
        """Обходить піддерево root і генерує markdown.

        Спільна логіка обходу для ``convert`` і content-density fallback
        (main-content та повний root).
        """
        md_parts: list[str] = []
        stats: ConvertStats = {"headings": 0, "links": 0, "images": 0, "code": 0, "lists": 0, "tables": 0, "rendered_links": 0}
        processed_elements: set[int] = set()

        # link_count — кількість href-anchor'ів у HTML (незалежно від
        # include_links). Семантика: скільки посилань було в документі.
        self._rendered_links = 0
        for a in root.find_children(["a"], recursive=True):
            if a.get_attribute("href"):
                stats["links"] += 1

        # Голий текст прямо в корені (типово <body>текст</body> без обгортки)
        # не належить жодному елементу, тож головний цикл його не бачив і
        # контент губився повністю.
        self._emit_root_bare_text(root, md_parts)

        for element in root.iter_descendants():
            elem_id = element.native_id
            if elem_id in processed_elements:
                continue

            self._dispatch_element(element, md_parts, stats, processed_elements)

        # rendered_links — скільки посилань реально вставлено у markdown.
        stats["rendered_links"] = self._rendered_links

        markdown = "\n".join(md_parts)

        if self._link_refs:
            markdown += "\n\n"
            for ref in self._link_refs:
                markdown += f"[{ref['id']}]: {ref['url']}\n"

        if self.options.normalize_whitespace and not getattr(
                self.options, "preserve_whitespace", False
        ):
            markdown = markdown.replace("\xa0", " ")
            markdown = _RE_NEWLINES.sub("\n\n", markdown)
            markdown = markdown.strip()

        max_wl = getattr(self.options, "max_word_length", 0)
        if max_wl and max_wl > 0:
            markdown = self._filter_long_words(markdown, max_wl)

        return markdown, stats

    def _emit_root_bare_text(self, root: HTMLElement, md_parts: list[str]) -> None:
        """Додає текстові вузли, що лежать прямо в корені, як параграф."""
        try:
            mixed = list(root.iter_direct_children_mixed())
        except (AttributeError, TypeError):
            return

        chunks = [str(value) for kind, value in mixed if kind == "text"]
        text = self._finalize_inline("".join(chunks))
        if text and len(text) >= self.options.min_paragraph_length:
            md_parts.append(f"\n{text}\n")

    def _dispatch_element(
            self,
            element: HTMLElement,
            md_parts: list[str],
            stats: dict[str, int],
            processed_elements: set[int],
    ) -> None:
        """Делегує елемент відповідному обробнику за тегом.

        Використовується головним циклом і mixed-content гілкою
        ``_process_container`` (block-діти обробляються рекурсивно у порядку
        DOM, без повернення в головний цикл).
        """
        tag_name = element.tag_name.lower()

        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._process_heading(element, md_parts, stats, processed_elements)
        elif tag_name in ("p", "figcaption"):
            self._process_paragraph(element, md_parts, processed_elements)
        elif tag_name == "pre" and self.options.include_code_blocks:
            self._process_code_block(element, md_parts, stats, processed_elements)
        elif tag_name in ("ul", "ol") and self.options.include_lists:
            self._process_list(element, md_parts, stats, processed_elements)
        elif tag_name == "blockquote" and self.options.include_blockquotes:
            self._process_blockquote(element, md_parts, processed_elements)
        elif tag_name == "img" and self.options.include_images:
            self._process_image(element, md_parts, stats, processed_elements)
        elif tag_name == "table" and self.options.include_tables:
            self._process_table(element, md_parts, stats, processed_elements)
        elif tag_name == "hr":
            md_parts.append("\n---\n")
            processed_elements.add(element.native_id)
        elif tag_name == "dl" and self.options.include_lists:
            # Definition list (Pandoc-style).
            self._process_definition_list(element, md_parts, stats, processed_elements)
        elif tag_name in (
            "div", "section", "aside", "span", "main", "article", "a", "figure",
            # Legacy / presentational wrappers: без них весь їхній текст
            # мовчки губився (bare <center>, <u>, <font>, <details>).
            "center", "u", "font", "details", "summary",
        ):
            self._process_container(element, md_parts, stats, processed_elements)

    def _process_heading(self, element: HTMLElement, md_parts: list[str], stats: dict[str, int], processed: set[int]) -> None:
        """Обробляє заголовок (h1-h6)."""
        level = int(element.tag_name[1])
        # get_text() у selectolax НЕ вставляє роздільник між дочірніми
        # вузлами, тому `<h2><span>Hello</span> <span>World</span></h2>`
        # злипався у `HelloWorld`. Рендеримо заголовок через inline-обхід
        # (він зберігає межі вузлів і inline-розмітку), а потім схлопуємо
        # усі переноси в пробіли — ATX-заголовок мусить бути однорядковим.
        text = element.get_text(strip=True)
        rendered = " ".join(self._process_inline(element).split())

        if rendered and len(text) >= self.options.min_heading_length:
            md_parts.append(f"\n{'#' * level} {rendered}\n")
            stats["headings"] += 1

        processed.add(element.native_id)
        for child in element.iter_descendants():
            processed.add(child.native_id)

    def _process_paragraph(self, element: HTMLElement, md_parts: list[str], processed: set[int]) -> None:
        """Обробляє параграф з inline форматуванням."""
        text = element.get_text(strip=True)
        md_text = self._process_inline(element)

        # Параграф із самим лише зображенням (у т.ч. <a><img></a>) не має
        # тексту — раніше він відкидався і картинка губилась повністю.
        media_only = not text and bool(md_text.strip())

        if md_text.strip() and (len(text) >= self.options.min_paragraph_length or media_only):
            md_parts.append(f"\n{md_text}\n")

        processed.add(element.native_id)
        for child in element.iter_descendants():
            processed.add(child.native_id)

    def _process_code_block(self, element: HTMLElement, md_parts: list[str], stats: dict[str, int], processed: set[int]) -> None:
        """Обробляє блок коду (pre)."""
        code = element.get_text(strip=False)

        if code and code.strip():
            code_elements = element.find_children(["code"], recursive=False)
            lang = ""

            if code_elements:
                code_elem = code_elements[0]
                classes = code_elem.get_attribute("class", "")

                # Мова визначається по окремих class-tokens, а не substring
                # на всьому рядку — уникаємо false-positive на `no-language-*`,
                # `js-no-language-picker`, `hljs-*`.
                lang = self._detect_code_language(classes)

                processed.add(code_elem.native_id)

            fence = self._fence_for(code)
            md_parts.append(f"\n{fence}{lang}\n{code.strip()}\n{fence}\n")
            stats["code"] += 1

        processed.add(element.native_id)

    # Highlighter-специфічні префікси/точні класи, з яких витягуємо мову
    _CODE_LANG_PREFIXES = ("language-", "lang-", "highlight-source-", "code-")
    # Class-токени, що точно НЕ є мовою, навіть якщо матчать префікс
    _CODE_LANG_NEGATIVE = frozenset({
        "language-none", "language-plain", "language-text",
        "lang-none", "lang-plain", "lang-text",
    })
    # Whitelist для формату `class="python"` без префікса
    _KNOWN_LANGS = frozenset({
        "python", "javascript", "typescript", "js", "ts", "jsx", "tsx",
        "java", "kotlin", "swift", "go", "rust", "ruby", "php",
        "c", "cpp", "csharp", "c++", "c#", "objc",
        "html", "css", "scss", "sass", "less",
        "json", "yaml", "yml", "toml", "xml", "sql", "bash", "sh", "shell", "zsh",
        "powershell", "ps1", "dockerfile", "makefile", "cmake",
        "markdown", "md", "tex", "latex",
        "r", "matlab", "julia", "scala", "haskell", "elixir", "erlang", "clojure",
        "lua", "perl", "dart", "diff", "graphql", "regex",
    })

    def _detect_code_language(self, class_str: str) -> str:
        """Витягує мову з `class` тега `<code>` за class-tokens (не substring).

        Підтримує формати: `language-python`, `lang-py`, `hljs-source-python`,
        `code-python`, а також exact-match для відомих мов (`class="python"`).
        Свідомо ігнорує `language-none`/`language-plain`/`language-text`.
        """
        if not class_str:
            return ""

        for token in class_str.split():
            t = token.lower()
            if t in self._CODE_LANG_NEGATIVE:
                continue
            for prefix in self._CODE_LANG_PREFIXES:
                if t.startswith(prefix) and len(t) > len(prefix):
                    return t[len(prefix):]
            if t in self._KNOWN_LANGS:
                return t
        return ""

    @staticmethod
    def _longest_backtick_run(s: str) -> int:
        """Довжина найдовшої суцільної послідовності backtick'ів у рядку."""
        longest = 0
        for m in re.finditer(r"`+", s):
            longest = max(longest, len(m.group()))
        return longest

    @staticmethod
    def _split_edge_ws(s: str) -> tuple[str, str, str]:
        """Розбиває рядок на ``(leading_ws, core, trailing_ws)``.

        Порожній / whitespace-only рядок → ``("", "", "")``.
        """
        core = s.strip()
        if not core:
            return "", "", ""
        return s[: len(s) - len(s.lstrip())], core, s[len(s.rstrip()):]

    @classmethod
    def _fence_for(cls, code: str) -> str:
        """Довжина backtick-fence: на 1 більша за найдовший run у коді (мін. 3)."""
        return "`" * max(3, cls._longest_backtick_run(code) + 1)

    @classmethod
    def _inline_code(cls, content: str) -> str:
        """Inline-код за CommonMark: делімітер довший за внутрішні backtick-runs,
        з паддінг-пробілом, якщо контент межує з backtick."""
        if not content:
            return ""
        delim = "`" * (cls._longest_backtick_run(content) + 1)
        pad = " " if (content.startswith("`") or content.endswith("`")) else ""
        return f"{delim}{pad}{content}{pad}{delim}"

    @classmethod
    def _emphasis(cls, inner: str, marker: str) -> str:
        """Обгортає ``inner`` у emphasis-маркери, виносячи крайові пробіли назовні.

        CommonMark забороняє пробіл одразу після відкриваючого / перед
        закриваючим маркером (``** bold **`` не працює), тож пробіли релокуються
        за межі, а порожній / whitespace-only вміст не лишає зіпсованих маркерів.
        """
        lead, core, trail = cls._split_edge_ws(inner)
        if not core:
            return ""
        return f"{lead}{marker}{core}{marker}{trail}"

    @staticmethod
    def _encode_url(url: str) -> str:
        """Percent-кодує пробіли/таби/переноси в URL (вони ламають markdown-синтаксис)."""
        if not url:
            return url
        return url.translate({0x20: "%20", 0x09: "%09", 0x0A: "%0A"})

    def _process_list(
            self,
            element: HTMLElement,
            md_parts: list[str],
            stats: dict[str, int],
            processed: set[int],
            indent: int = 0,
    ) -> None:
        """Обробляє список (ul/ol) з вкладеністю."""
        list_md = self._list_to_markdown(element, indent)

        if list_md:
            md_parts.append(f"\n{list_md}\n")
            stats["lists"] += 1

        for child in element.iter_descendants():
            processed.add(child.native_id)

        processed.add(element.native_id)

    def _list_to_markdown(self, element: HTMLElement, indent: int = 0) -> str:
        """Конвертує список в Markdown з підтримкою вкладеності.

        Підтримує GFM task-list (``<input type="checkbox">`` →
        ``- [x] ...`` / ``- [ ] ...``) та bullet cycling — символ маркера
        для UL береться з ``options.bullets`` за глибиною:
        ``bullets[depth % len(bullets)]``.
        """
        lines = []
        indent_str = "  " * indent
        is_ordered = element.tag_name == "ol"

        # Bullet cycling за рівнем вкладеності.
        bullets = getattr(self.options, "bullets", "-") or "-"
        bullet = bullets[indent % len(bullets)]

        list_items = element.find_children(["li"], recursive=False)

        # <ol start="5"> — нумерація мусить починатися з 5, а не з 1.
        start = 1
        if is_ordered:
            raw_start = (element.get_attribute("start", "") or "").strip()
            if raw_start:
                try:
                    start = int(raw_start)
                except ValueError:
                    start = 1

        for i, li in enumerate(list_items, start if is_ordered else 1):
            # GFM task-list — шукаємо безпосередній <input type=checkbox>.
            checkbox_marker = self._extract_task_marker(li)

            try:
                mixed_children = list(li.iter_direct_children_mixed())
            except (AttributeError, TypeError):
                mixed_children = []

            inline_parts: list[str] = []
            block_paras: list[str] = []
            nested_lists: list[HTMLElement] = []
            for kind, value in mixed_children:
                if kind == "text":
                    inline_parts.append(self._render_inline_node("text", value))
                elif kind == "element":
                    child_tag = value.tag_name.lower()
                    if child_tag in ("ul", "ol"):
                        nested_lists.append(value)
                    elif child_tag == "p":
                        # Кілька <p> у <li> → окремі параграфи (loose list).
                        para = " ".join(self._process_inline(value).split()).strip()
                        if para:
                            block_paras.append(para)
                    else:
                        inline_parts.append(self._render_inline_node("element", value.native))

            lead_text = " ".join(self._finalize_inline("".join(inline_parts)).split()).strip()
            segments = [s for s in ([lead_text] + block_paras) if s]
            text = "\n\n".join(segments)

            if text:
                prefix = f"{i}." if is_ordered else bullet
                if checkbox_marker is not None:
                    lines.append(f"{indent_str}{prefix} {checkbox_marker} {text}")
                else:
                    lines.append(f"{indent_str}{prefix} {text}")

            for nested in nested_lists:
                nested_md = self._list_to_markdown(nested, indent + 1)
                if nested_md:
                    lines.append(nested_md)

        return "\n".join(lines)

    def _extract_task_marker(self, li: HTMLElement) -> str | None:
        """Повертає GFM task-list маркер для ``<li>`` або ``None``.

        Шукає ``<input type="checkbox">`` серед дітей ``<li>``. Якщо є
        атрибут ``checked`` — ``[x]``, інакше ``[ ]``. Якщо чекбоксу нема —
        повертає ``None``, і список рендериться як звичайний.
        """
        try:
            inputs = li.find_children(["input"], recursive=True)
        except Exception:
            return None

        for inp in inputs:
            input_type = (inp.get_attribute("type", "") or "").lower()
            if input_type != "checkbox":
                continue
            # `checked` у HTML5 — boolean attribute: <input checked> валідно.
            # BS4 зберігає його як '' (порожній рядок), Selectolax — як None.
            # Наш get_attribute() повертає default для обох (str(value) if value),
            # тому дивимося у нативний attrs dict напряму (parser-agnostic).
            native = getattr(inp, "native", None)
            attrs = getattr(native, "attrs", None) or getattr(native, "attributes", None) or {}
            is_checked = "checked" in attrs
            return "[x]" if is_checked else "[ ]"

        return None

    def _process_definition_list(
            self,
            element: HTMLElement,
            md_parts: list[str],
            stats: dict[str, int],
            processed: set[int],
    ) -> None:
        """Обробляє definition list (``<dl>``) у Pandoc-стилі.

        Формат виводу::

            term
            : definition

        Підтримує множинні ``<dd>`` для одного ``<dt>`` (всі ``<dd>``,
        що йдуть до наступного ``<dt>``, прив'язуються до останнього
        зустрінутого терміна).
        """
        children = element.find_children(["dt", "dd"], recursive=False)
        if not children:
            processed.add(element.native_id)
            return

        lines: list[str] = []
        current_term: str | None = None

        for child in children:
            tag = child.tag_name.lower()
            text = self._process_inline(child)
            text = " ".join(text.split()).strip()
            if not text:
                continue

            if tag == "dt":
                if current_term is not None and lines and lines[-1] != "":
                    lines.append("")
                lines.append(text)
                current_term = text
            elif tag == "dd":
                # Якщо <dd> зустрінувся без попереднього <dt> — рендеримо
                # як осиротілу definition (це валідний Pandoc edge-case).
                lines.append(f": {text}")

        if lines:
            md_parts.append("\n" + "\n".join(lines) + "\n")
            stats["lists"] += 1

        for d in element.iter_descendants():
            processed.add(d.native_id)
        processed.add(element.native_id)

    def _process_blockquote(self, element: HTMLElement, md_parts: list[str], processed: set[int]) -> None:
        """Обробляє blockquote зі збереженням блоків (pre→fence, списки, вкладені bq)."""
        quoted = self._render_blockquote(element)
        if quoted:
            md_parts.append(f"\n{quoted}\n")

        for child in element.iter_descendants():
            processed.add(child.native_id)
        processed.add(element.native_id)

    def _render_blockquote(self, element: HTMLElement) -> str:
        """Рендерить blockquote у ``> ``-префіксований markdown.

        Вкладені ``<blockquote>`` отримують додатковий рівень ``> `` (справжня
        багаторівнева цитата ``> > text`` за CommonMark), а не схлопуються в один.
        """
        inner = self._blockquote_inner(element)
        if not inner.strip():
            return ""
        lines = inner.split("\n")
        return "\n".join(f"> {line}" if line.strip() else ">" for line in lines)

    def _blockquote_inner(self, element: HTMLElement) -> str:
        """Рендерить вміст blockquote, зберігаючи блокові діти окремими сегментами.

        ``<pre>`` → fenced code block, ``<ul>/<ol>`` → список, ``<p>`` →
        окремий параграф, вкладений ``<blockquote>`` → додатковий рівень
        цитати (``> > …``). Текст/inline між блоками групується у власні
        параграфи. Сегменти з'єднуються ``\\n\\n``.
        """
        try:
            mixed = list(element.iter_direct_children_mixed())
        except (AttributeError, TypeError):
            return self._process_inline(element)

        segments: list[str] = []
        inline_buf: list[str] = []

        def flush_inline() -> None:
            if not inline_buf:
                return
            txt = self._finalize_inline("".join(inline_buf))
            if txt.strip():
                segments.append(txt.strip())
            inline_buf.clear()

        for kind, value in mixed:
            if kind == "text":
                inline_buf.append(self._render_inline_node("text", value))
                continue

            tag = value.tag_name.lower()
            if tag == "pre" and self.options.include_code_blocks:
                flush_inline()
                code = value.get_text(strip=False)
                if code.strip():
                    fence = self._fence_for(code)
                    lang = self._detect_pre_lang(value)
                    segments.append(f"{fence}{lang}\n{code.strip()}\n{fence}")
            elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                flush_inline()
                htext = " ".join(self._process_inline(value).split()).strip()
                if htext:
                    segments.append(f"{'#' * int(tag[1])} {htext}")
            elif tag == "hr":
                flush_inline()
                segments.append("---")
            elif tag == "blockquote" and self.options.include_blockquotes:
                flush_inline()
                nested = self._render_blockquote(value)
                if nested:
                    segments.append(nested)
            elif tag in ("ul", "ol") and self.options.include_lists:
                flush_inline()
                lst = self._list_to_markdown(value)
                if lst.strip():
                    segments.append(lst.strip())
            elif tag == "p":
                flush_inline()
                para = self._process_inline(value)
                if para.strip():
                    segments.append(para.strip())
            else:
                inline_buf.append(self._render_inline_node("element", value.native))

        flush_inline()
        return "\n\n".join(segments)

    def _detect_pre_lang(self, pre_el: HTMLElement) -> str:
        """Мова коду з першого ``<code>`` у ``<pre>`` (за class-token)."""
        codes = pre_el.find_children(["code"], recursive=False)
        if codes:
            return self._detect_code_language(codes[0].get_attribute("class", ""))
        return ""

    def _process_image(self, element: HTMLElement, md_parts: list[str], stats: dict[str, int], processed: set[int]) -> None:
        """Обробляє зображення."""
        src = element.get_attribute("src", "")
        alt = element.get_attribute("alt", "")

        if src:
            # Нормалізуємо URL зображення
            if self.options.normalize_urls and self.options.base_url:
                src = self._normalize_url(src)
            src = self._encode_url(src)

            md_parts.append(f"\n![{alt}]({src})\n")
            stats["images"] += 1

        processed.add(element.native_id)

    def _process_table(self, element: HTMLElement, md_parts: list[str], stats: dict[str, int], processed: set[int]) -> None:
        """Обробляє таблицю."""
        table_md = self._table_to_markdown(element)

        if table_md and table_md.strip():
            md_parts.append(f"\n{table_md}\n")
            stats["tables"] += 1

        for child in element.iter_descendants():
            processed.add(child.native_id)

        processed.add(element.native_id)

    # Внутрішній маркер розриву рядка в клітинці (br / межа блоку / пункт
    # списку / рядок вкладеної таблиці). Не існує у вхідному тексті, тому
    # безпечний як роздільник до фінального схлопування у ``<br>``.
    _CELL_BR = "\x00CELLBR\x00"
    _RE_WS = re.compile(r"\s+")

    def _table_to_markdown(self, table: HTMLElement) -> str:
        """Конвертує HTML-таблицю в Markdown з повною матеріалізацією сітки.

        Дві фази (див. `_materialize_grid` та емісію нижче):

        1. **Матеріалізація** — `thead` і тіло розкладаються в 2D-матриці з
           протягуванням значень по `rowspan`/`colspan` (обидва — повтор
           значення).
        2. **Емісія** — усі рядки вирівнюються до `max_cols`, заголовок
           (`thead`-матриця або перший `th`-рядок, або синтетичні `Col N`)
           склеюється вертикально в один рядок, далі `| ... |` + сепаратор.
        """
        thead_tr_ids: set[int] = set()
        header_grid: list[list[str]] | None = None

        thead_elements = table.find_children(["thead"], recursive=False)
        if thead_elements:
            thead = thead_elements[0]
            head_trs = thead.find_children(["tr"], recursive=False)
            for t in head_trs:
                thead_tr_ids.add(t.native_id)
            if head_trs:
                header_grid = self._materialize_grid(head_trs)

        # Тіло: рядки з усіх <tbody> та <tfoot> плюс прямі <tr> таблиці, у
        # порядку документа. <tfoot> НЕ втрачається (реальні дані підсумків);
        # <thead>-рядки виключені; рекурсія не заходить у вкладені таблиці.
        body_trs: list[HTMLElement] = []
        for child in table.find_children(["tbody", "tfoot", "tr"], recursive=False):
            ctag = child.tag_name.lower()
            if ctag in ("tbody", "tfoot"):
                body_trs.extend(child.find_children(["tr"], recursive=False))
            elif child.native_id not in thead_tr_ids:
                body_trs.append(child)

        # Заголовок без <thead>: перший рядок цілком із <th> → він header.
        first_row_is_header = False
        if header_grid is None and body_trs:
            first_cells = body_trs[0].find_children(["td", "th"], recursive=False)
            first_row_is_header = bool(first_cells) and all(
                c.tag_name.lower() == "th" for c in first_cells
            )

        body_grid = self._materialize_grid(body_trs)

        if header_grid is None and first_row_is_header and body_grid:
            header_grid = [body_grid[0]]
            body_grid = body_grid[1:]

        if header_grid is None and not body_grid:
            return ""

        # Ширина = максимум серед усіх матеріалізованих рядків (header + body).
        max_cols = 0
        for g in (header_grid or []), body_grid:
            for row in g:
                if len(row) > max_cols:
                    max_cols = len(row)
        if max_cols == 0:
            return ""

        if header_grid is not None:
            header_cells = self._flatten_header(header_grid, max_cols)
        else:
            # Немає <thead> і перший рядок не суто-th → синтетичний заголовок,
            # а перший матеріалізований рядок лишається серед даних.
            header_cells = [f"Col {i + 1}" for i in range(max_cols)]

        rows_out: list[str] = []
        rows_out.append("| " + " | ".join(self._pad_row(header_cells, max_cols)) + " |")
        rows_out.append("| " + " | ".join(["---"] * max_cols) + " |")
        for row in body_grid:
            rows_out.append("| " + " | ".join(self._pad_row(row, max_cols)) + " |")

        return "\n".join(rows_out)

    @staticmethod
    def _pad_row(row: list[str], width: int) -> list[str]:
        """Добиває короткий рядок `" "` справа до `width`."""
        if len(row) >= width:
            return row[:width]
        return list(row) + [" "] * (width - len(row))

    def _flatten_header(self, grid: list[list[str]], width: int) -> list[str]:
        """Склеює багатоярусний `thead` в один рядок заголовка.

        Для кожної фінальної колонки беремо мітки ярусів зверху вниз,
        прибираємо порожні та послідовні дублікати (клітинка з `rowspan`
        дає одну й ту саму мітку в кількох ярусах → одна мітка) і з'єднуємо
        пробілом. GFM дозволяє лише один рядок заголовка.
        """
        result: list[str] = []
        for col in range(width):
            labels: list[str] = []
            for row in grid:
                val = row[col] if col < len(row) else " "
                val = val.strip()
                if not val:
                    continue
                if labels and labels[-1] == val:
                    continue
                labels.append(val)
            result.append(" ".join(labels) if labels else " ")
        return result

    def _materialize_grid(self, trs: list[HTMLElement]) -> list[list[str]]:
        """Матеріалізує список `<tr>` у 2D-матрицю значень.

        `active` тримає вертикальні спани: `col -> (rows_left, value)`.
        Для кожного рядка спершу заповнюються колонки з активних спанів,
        потім розкладаються власні клітинки з урахуванням `colspan` (повтор
        значення), а клітинки з `rowspan>1`/`rowspan=0` реєструють активний
        спан на наступні рядки.
        """
        n = len(trs)
        active: dict[int, tuple[int, str]] = {}
        grid: list[list[str]] = []

        for row_idx, tr in enumerate(trs):
            remaining_rows = n - row_idx  # від поточного до кінця, включно
            cells = tr.find_children(["td", "th"], recursive=False)

            rendered: list[tuple[str, int, int]] = []
            for cell in cells:
                value = self._render_cell(cell)
                colspan = self._parse_colspan(cell.get_attribute("colspan", "1"))
                rowspan = self._parse_rowspan(
                    cell.get_attribute("rowspan", "1"), remaining_rows
                )
                rendered.append((value, colspan, rowspan))

            row: list[str] = []
            col = 0
            ci = 0
            while ci < len(rendered) or col in active:
                if col in active:
                    rows_left, val = active[col]
                    row.append(val)
                    if rows_left - 1 > 0:
                        active[col] = (rows_left - 1, val)
                    else:
                        del active[col]
                    col += 1
                    continue

                value, colspan, rowspan = rendered[ci]
                ci += 1
                for _ in range(colspan):
                    row.append(value)
                    if rowspan > 1:
                        active[col] = (rowspan - 1, value)
                    col += 1

            grid.append(row)

        return grid

    @staticmethod
    def _parse_colspan(raw: str) -> int:
        """`colspan` → int ≥ 1. Невалідне/`≤0` → `1`."""
        try:
            val = int(raw)
        except (ValueError, TypeError):
            return 1
        return val if val >= 1 else 1

    @staticmethod
    def _parse_rowspan(raw: str, remaining_rows: int) -> int:
        """`rowspan` → кількість рядків, які накриває клітинка.

        - `0` → до кінця секції (усі рядки, що лишились, окрім останнього,
          де може стояти власна клітинка тієї ж колонки);
        - невалідне / `<0` → `1`;
        - більше за наявні рядки → обрізається (без фантомних рядків).
        """
        try:
            val = int(raw)
        except (ValueError, TypeError):
            return 1
        if val == 0:
            return max(1, remaining_rows - 1)
        if val < 0:
            return 1
        return min(val, remaining_rows)

    def _render_cell(self, cell: HTMLElement) -> str:
        """Рендерить вміст клітинки у один рядок Markdown-таблиці.

        Inline-форматування (strong/em/code/del/лінки/`<br>`), вкладені
        списки (пункти через `<br>`) та вкладені таблиці (комірки через
        ` / `, рядки через `<br>`) серіалізуються, після чого значення
        екранується для таблиці (`|` → `\\|`, реальні переноси → `<br>`).
        """
        raw = self._render_cell_node(cell)
        raw = html.unescape(raw)

        lines: list[str] = []
        for seg in raw.split(self._CELL_BR):
            seg = self._RE_WS.sub(" ", seg).strip()
            if seg:
                lines.append(seg)

        text = "<br>".join(lines)
        text = text.replace("|", "\\|")
        return text if text else " "

    def _render_cell_node(self, el: HTMLElement) -> str:
        """Рекурсивний рендер піддерева клітинки з `_CELL_BR`-маркерами.

        Текст — як є; `<br>`/блоки/пункти списку/рядки вкладеної таблиці —
        через `_CELL_BR`. Фінальне схлопування робить `_render_cell`.
        """
        preserve_fmt = getattr(self.options, "preserve_inline_formatting", True)
        parts: list[str] = []

        try:
            children = list(el.iter_direct_children_mixed())
        except (AttributeError, TypeError):
            return el.get_text(strip=True)

        for kind, value in children:
            if kind == "text":
                parts.append(str(value))
                continue

            tag = value.tag_name.lower()

            if tag == "br":
                parts.append(self._CELL_BR)
            elif tag in ("ul", "ol"):
                items = [
                    self._render_cell_node(li)
                    for li in value.find_children(["li"], recursive=False)
                ]
                parts.append(self._CELL_BR + self._CELL_BR.join(items) + self._CELL_BR)
            elif tag == "table":
                parts.append(self._CELL_BR + self._render_nested_table(value) + self._CELL_BR)
            elif tag in ("p", "div", "section", "article", "li", "tr"):
                parts.append(self._CELL_BR + self._render_cell_node(value) + self._CELL_BR)
            elif preserve_fmt and tag in ("strong", "b"):
                parts.append(f"**{self._render_cell_node(value)}**")
            elif preserve_fmt and tag in ("em", "i"):
                parts.append(f"*{self._render_cell_node(value)}*")
            elif preserve_fmt and tag == "code":
                parts.append(f"`{self._render_cell_node(value)}`")
            elif preserve_fmt and tag in ("del", "s", "strike"):
                parts.append(f"~~{self._render_cell_node(value)}~~")
            elif tag == "a" and self.options.include_links:
                href = value.get_attribute("href", "")
                if href and self.options.normalize_urls and self.options.base_url:
                    href = self._normalize_url(href)
                inner = self._render_cell_node(value).strip()
                if href and inner:
                    self._rendered_links += 1
                    if getattr(self.options, "link_style", "inline") == "reference":
                        self._ref_counter += 1
                        ref_id = self._ref_counter
                        self._link_refs.append({"id": ref_id, "url": href})
                        parts.append(f"[{inner}][{ref_id}]")
                    else:
                        parts.append(f"[{inner}]({href})")
                else:
                    parts.append(inner)
            else:
                parts.append(self._render_cell_node(value))

        return "".join(parts)

    def _render_nested_table(self, table: HTMLElement) -> str:
        """Серіалізує вкладену таблицю: комірки через ` / `, рядки через `<br>`.

        Не додає рядків/колонок у зовнішню таблицю — усе лишається в межах
        однієї клітинки. Береться ЛИШЕ ВЛАСНІ рядки таблиці (прямі <tr> та
        <tr> у прямих <thead>/<tbody>/<tfoot>); рядки ще глибше вкладених
        таблиць не дублюються (вони серіалізуються всередині своєї клітинки).
        """
        own_trs: list[HTMLElement] = []
        for child in table.find_children(["thead", "tbody", "tfoot", "tr"], recursive=False):
            if child.tag_name.lower() in ("thead", "tbody", "tfoot"):
                own_trs.extend(child.find_children(["tr"], recursive=False))
            else:
                own_trs.append(child)

        rows: list[str] = []
        for tr in own_trs:
            cell_texts = []
            for c in tr.find_children(["td", "th"], recursive=False):
                inner = self._render_cell_node(c).replace(self._CELL_BR, " ")
                inner = self._RE_WS.sub(" ", inner).strip()
                cell_texts.append(inner)
            if cell_texts:
                rows.append(" / ".join(cell_texts))
        return self._CELL_BR.join(rows)

    # ASCII punctuation, що може починати inline-конструкцію у CommonMark.
    # Ми НЕ екрануємо те, що вже використовується як наш згенерований
    # markdown (``**``, ``*`` для strong/em, `` ` `` для code тощо). Тому
    # escape застосовується ТІЛЬКИ до text-сегментів HTML-входу, ще ДО
    # того як regex-заміни згенерують markers. Див. ``_escape_text_nodes_in_html``.
    _CM_ESCAPE_RE = re.compile(r"([\\`*_{}\[\]()#+\-!~|])")

    @classmethod
    def _escape_commonmark_text(cls, text: str) -> str:
        """Екранує CommonMark/GFM спецсимволи у plain-text.

        Використовується для тексту з ``get_text()`` (там немає HTML-тегів,
        що могли б згенерувати markers). Код-інлайн / посилання / таблиці
        викликають цей метод через власні гілки, бо контекст різний.
        """
        if not text:
            return text
        return cls._CM_ESCAPE_RE.sub(r"\\\1", text)

    @staticmethod
    def _filter_long_words(text: str, max_length: int) -> str:
        """Видаляє слова довші за max_length (CSS/class-name garbage).

        Не чіпає URL (містять ``://``), markdown-посилання ``](…)``,
        code-fences та reference-defs.
        """
        if not text or max_length <= 0:
            return text

        def replacer(m):
            word = m.group(0)
            if "://" in word or word.startswith("![") or word.startswith("["):
                return word
            if word.startswith("```") or word.startswith("[ref"):
                return word
            return ""

        return _RE_LONG_WORD.sub(replacer, text)

    @classmethod
    def _escape_text_nodes_in_html(cls, html_str: str) -> str:
        """Екранує CommonMark-спецсимволи тільки у ТЕКСТОВИХ сегментах HTML.

        Проходить html_str ззовні ``<...>`` тегів та екранує спецсимволи у
        текстових регіонах. HTML-теги (і HTML-атрибути всередині них)
        залишаються недоторканими, тому подальші regex-заміни коректно
        перетворюють ``<strong>`` → ``**`` без хибного екранування.

        **Контекстно** пропускає вміст ``<code>``/``<pre>``/``<kbd>``/
        ``<samp>`` — усередині них CommonMark забороняє escape.
        Також пропускає ``<a>`` (текст посилання залишаємо як є, бо він
        фінальний — без перекладу у markers).

        HTML-entities (``&amp;`` / ``&lt;``) залишаємо — вони нормалізуються
        пізніше через ``html.unescape`` і на markdown-рендер не впливають.
        """
        if not html_str or "<" not in html_str:
            return cls._escape_commonmark_text(html_str)

        # Теги, всередині яких escape НЕ застосовується.
        skip_tags = {"code", "pre", "kbd", "samp", "a"}
        out: list[str] = []
        i = 0
        n = len(html_str)
        tag_re = _RE_TAG_PARSE

        while i < n:
            m = tag_re.search(html_str, i)
            if not m:
                out.append(cls._escape_commonmark_text(html_str[i:]))
                break
            # Текст до тега — escape
            if m.start() > i:
                out.append(cls._escape_commonmark_text(html_str[i : m.start()]))
            tag_full = m.group(0)
            is_close = m.group(1) == "/"
            tag_name = m.group(2).lower()
            out.append(tag_full)
            i = m.end()

            if not is_close and tag_name in skip_tags:
                # Знайти відповідний закриваючий тег — скіпаємо вміст.
                close_re = re.compile(r"</" + re.escape(tag_name) + r"\s*>", re.IGNORECASE)
                cm = close_re.search(html_str, i)
                if cm:
                    out.append(html_str[i : cm.end()])
                    i = cm.end()
                else:
                    out.append(html_str[i:])
                    i = n
        return "".join(out)

    def _process_container(self, element: HTMLElement, md_parts: list[str], stats: dict[str, int], processed: set[int]) -> None:
        """Обробляє контейнери (div, section, aside, span, a, figure, …).

        Гілки обробки:

        0. **``<a>`` без блокових дітей (окрім ``<img>``)** — увесь anchor
           рендериться як inline-лінк (у т.ч. image-link ``[![alt](src)](href)``);
           ``<a>`` з блоковими дітьми (напр. ``<a><h2>``) йде у гілку 2.
        1. **Без block-дітей** — увесь вміст інлайновий, генеруємо один
           параграф через ``_process_inline``.
        2. **Mixed content** — block-теги перемежовані з текстом/inline-
           елементами як прямі діти. Block-діти диспатчимо рекурсивно
           через ``_dispatch_element`` У ПОРЯДКУ DOM, а text + inline між
           ними згруповуємо у віртуальні параграфи. Це покриває кейс,
           коли всередині ``<div>`` є текст і ``<strong>``-заголовки
           поза ``<p>``-обгортками (типовий Bootstrap-патерн).

        Усі нащадки контейнера, опрацьовані тут, мітяться у ``processed``,
        щоб головний цикл ``_convert_subtree`` не дублював вивід.
        """
        # Block-теги, які мають власний обробник. Широкий список — щоб
        # mixed-content фолбек не дублював уже відрендерений block-контент.
        block_tags = {
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "table",
            "pre",
            "blockquote",
            "div",
            "section",
            "article",
            "aside",
            "dl",
            "hr",
            "img",
            "figure",
            "form",
            "nav",
            "header",
            "footer",
            "main",
            "a",
            "figcaption",
        }

        # Дешева перевірка через адаптер (без повного списку дітей).
        has_block_children = element.has_children(list(block_tags))

        # <a> як контейнер: якщо немає блокових дітей окрім <img> — рендеримо
        # цілий anchor як inline-лінк (у т.ч. image-link ``[![alt](src)](href)``).
        # Інакше (напр. <a><h2>Title</h2></a>) блокові діти обробляться нижче.
        if element.tag_name.lower() == "a":
            block_non_img = [t for t in block_tags if t != "img"]
            if not element.has_children(block_non_img):
                md_text = self._finalize_inline(
                    self._render_inline_node("element", element.native)
                )
                if md_text.strip():
                    md_parts.append(f"\n{md_text}\n")
                for child in element.iter_descendants():
                    processed.add(child.native_id)
                processed.add(element.native_id)
                return

        if not has_block_children:
            if getattr(self.options, "extract_div_text", True):
                text = element.get_text(strip=True)
                if text and len(text) >= self.options.min_paragraph_length:
                    md_text = self._process_inline(element)
                    md_parts.append(f"\n{md_text}\n")

            for child in element.iter_descendants():
                processed.add(child.native_id)
            processed.add(element.native_id)
            return

        # Mixed content: ходимо ПРЯМИМИ дітьми, інлайн-сегменти збираємо
        # у буфер, block-діти диспатчимо рекурсивно у порядку DOM.
        try:
            mixed = list(element.iter_direct_children_mixed())
        except (AttributeError, TypeError):
            # Адаптер без mixed-iter — нічого не робимо (block-діти
            # обробляться головним циклом, інлайн-mixed втрачається,
            # але хоча б нічого не падає).
            return

        inline_buffer: list[tuple[str, object]] = []

        def flush() -> None:
            if not inline_buffer:
                return
            # Inline-сегменти рендеримо прямим обходом дерева
            # (_render_inline_node): текст — як є (з опційним strict-escape),
            # елементи — рекурсивним tree-walk. Уникаємо serialize→parse
            # циклу (BS4 Tag.decode() — O(subtree) на кожен inline-child).
            strict = getattr(self.options, "strict_escape", False)
            parts: list[str] = []
            for kind, value in inline_buffer:
                if kind == "text":
                    parts.append(self._escape_commonmark_text(value) if strict else value)
                else:  # element (HTMLElement)
                    parts.append(self._render_inline_node("element", value.native))
            md_text = self._finalize_inline("".join(parts))
            stripped = md_text.strip() if md_text else ""
            if stripped and len(stripped) >= self.options.min_paragraph_length:
                md_parts.append(f"\n{md_text}\n")

            for kind, value in inline_buffer:
                if kind != "element":
                    continue
                processed.add(value.native_id)
                try:
                    for desc in value.iter_descendants():
                        processed.add(desc.native_id)
                except (AttributeError, TypeError):
                    pass

            inline_buffer.clear()

        for kind, value in mixed:
            if kind == "text":
                inline_buffer.append(("text", value))
                continue

            # kind == 'element'
            tag = value.tag_name.lower()
            if tag in block_tags:
                # <a> with block children (e.g. <a><h2>Title</h2></a>) —
                # dispatch as container so block children are processed.
                # <a> without block children — treat as inline link.
                if tag == "a" and not value.has_children(list(block_tags)):
                    inline_buffer.append(("element", value))
                    continue
                flush()
                if value.native_id not in processed:
                    self._dispatch_element(value, md_parts, stats, processed)
                continue

            # Inline-елемент: буферизуємо як tree-fragment (не HTML-string).
            inline_buffer.append(("element", value))

        flush()

        # Block children are marked by their own handlers; inline children
        # are marked by flush(). No need for a full iter_descendants sweep
        # (eliminates the quadratic performance bottleneck).
        processed.add(element.native_id)

    def _html_fragment_to_markdown(self, html_str: str) -> str:
        """Конвертує HTML-фрагмент (string, без єдиного кореня) у Markdown.

        Приймає вже готовий HTML-string і застосовує regex-заміни inline-
        тегів. Потрібно для mixed-content: коли треба склеїти
        text + inline + text + inline між block-дітьми у один віртуальний
        параграф.

        Підтримує: ``<br>``, ``<code>``, ``<strong>/<b>``, ``<em>/<i>``,
        ``<del>/<s>/<strike>``, ``<a>`` (за ``options.include_links``),
        strict_escape (за ``options.strict_escape``), CommonMark hard-break.
        """
        if not html_str:
            return ""

        # strict_escape — екранує спецсимволи у text-сегментах ДО regex-replace.
        if getattr(self.options, "strict_escape", False):
            html_str = self._escape_text_nodes_in_html(html_str)

        result = html_str

        ns = getattr(self.options, "newline_style", "spaces") or "spaces"
        hard_break = "\\\n" if ns == "backslash" else "  \n"

        result = _RE_BR.sub(hard_break, result)

        if getattr(self.options, "preserve_inline_formatting", True):
            result = _RE_CODE.sub(r"`\1`", result)
            result = _RE_STRONG.sub(r"**\1**", result)
            result = _RE_EM.sub(r"*\1*", result)
            result = _RE_DEL.sub(r"~~\1~~", result)

        if self.options.include_links:
            link_style = getattr(self.options, "link_style", "inline")

            def replace_link(match):
                href_match = _RE_HREF.search(match.group(1))
                href = href_match.group(1) if href_match else ""
                text = match.group(2)

                if href and self.options.normalize_urls and self.options.base_url:
                    href = self._normalize_url(href)

                text = _RE_TAG_STRIP.sub(" ", text)
                text = text.strip()

                if href and text:
                    self._rendered_links += 1
                    if link_style == "reference":
                        self._ref_counter += 1
                        ref_id = self._ref_counter
                        self._link_refs.append({"id": ref_id, "url": href})
                        return f"[{text}][{ref_id}]"
                    return f"[{text}]({href})"
                return text

            result = _RE_LINK.sub(replace_link, result)
        else:
            result = _RE_LINK_STRIP.sub(r"\1", result)

        # Видаляємо інші теги (span, etc.) лишаючи їхній текст.
        # Replace with space to prevent word concatenation.
        result = _RE_TAG_STRIP.sub(" ", result)
        result = html.unescape(result)

        # Зберігаємо hard-break до нормалізації пробілів.
        placeholder = "\x00HARDBREAK\x00"
        result = _RE_HARDBREAK_SPACES.sub(placeholder, result)
        result = _RE_HARDBREAK_BACKSLASH.sub(placeholder, result)
        preserve_ws = getattr(self.options, "preserve_whitespace", False)
        result = result.replace("\xa0", " ")
        if not preserve_ws:
            result = _RE_TABS.sub(" ", result)
            result = _RE_NL_TRIM.sub("\n", result)
            result = _RE_NEWLINES.sub("\n\n", result)
        result = result.replace(placeholder, hard_break)

        return result.strip() if not preserve_ws else result

    def _process_inline(self, element: HTMLElement) -> str:
        """Конвертує inline-вміст елемента у Markdown обходом дерева.

        Обхід дерева природно обробляє вкладені теги: ``<strong><em>x</em>
        </strong>`` → ``***x***``.
        """
        return self._process_inline_tree(element)

    def _process_inline_tree(self, element: HTMLElement) -> str:
        """Обхід дерева для inline-форматування (parser-agnostic).

        Обходить дочірні вузли елемента рекурсивно, природно обробляючи
        вкладені теги (наприклад, <strong><em>текст</em></strong> стає
        ***текст***).
        """
        parts = [
            self._render_inline_node(kind, node)
            for kind, node in self._iter_inline_children(element.native)
        ]
        return self._finalize_inline("".join(parts))

    def _iter_inline_children(self, node):
        """Прямі діти НАТИВНОГО вузла як (kind, native) tuples.

        Підтримує BS4 (``Tag.children`` → ``Tag``/``NavigableString``) та
        Selectolax (``Node.iter(include_text=True)`` → ``Node`` з
        ``tag == '-text'``). Повертає нативні вузли (не HTMLElement) —
        рендер робить ``_render_inline_node``.
        """
        if hasattr(node, "iter"):
            try:
                for child in node.iter(include_text=True):
                    tag = getattr(child, "tag", None)
                    if not tag:
                        continue
                    if tag == "-text":
                        try:
                            raw = child.text(deep=False, strip=False) or ""
                        except TypeError:
                            raw = child.text() or ""
                        if raw:
                            yield ("text", raw)
                    elif tag.startswith("-") or tag.startswith("!"):
                        continue
                    else:
                        yield ("element", child)
                return
            except TypeError:
                pass

        if hasattr(node, "children"):
            for child in node.children:
                if isinstance(child, Comment):
                    continue
                if isinstance(child, NavigableString):
                    yield ("text", str(child))
                    continue
                if isinstance(child, Tag):
                    yield ("element", child)

    # Block-рівневі теги, які можуть трапитись під час inline-обходу
    # (у blockquote, li, td). Кожен такий вузол дає порожній рядок навколо
    # себе, інакше сусідні блоки злипаються в одне слово.
    _INLINE_BLOCK_BOUNDARY = frozenset({
        "p", "div", "blockquote", "section", "article", "aside", "figure",
        "figcaption", "header", "footer", "main", "pre", "dl", "dt", "dd",
        "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "address",
    })

    def _render_inline_node(self, kind, node) -> str:
        """Рекурсивно рендерить один inline-вузол у Markdown.

        Спільний рендер для ``_process_inline_tree`` та mixed-content буфера
        у ``_process_container``. Inline-діти рендеряться прямим обходом
        дерева — без серіалізації у HTML-рядок і повторного regex-парсингу.
        """
        ns = getattr(self.options, "newline_style", "spaces") or "spaces"
        hard_break = "\\\n" if ns == "backslash" else "  \n"

        if kind == "text":
            text = str(node)
            if text and getattr(self.options, "strict_escape", False):
                text = self._escape_commonmark_text(text)
            return text

        tag = ""
        if hasattr(node, "name") and node.name:
            tag = node.name.lower()
        elif hasattr(node, "tag") and node.tag:
            tag = node.tag.lower()

        if tag == "br":
            return hard_break

        if tag == "img":
            if not self.options.include_images:
                return ""
            src = ""
            alt = ""
            if hasattr(node, "get"):
                src = node.get("src", "") or ""
                alt = node.get("alt", "") or ""
            elif hasattr(node, "attributes"):
                attrs = node.attributes or {}
                src = attrs.get("src", "") or ""
                alt = attrs.get("alt", "") or ""
            if not src:
                return ""
            if self.options.normalize_urls and self.options.base_url:
                src = self._normalize_url(src)
            src = self._encode_url(src)
            return f"![{alt}]({src})"

        inner = "".join(
            self._render_inline_node(ck, cn) for ck, cn in self._iter_inline_children(node)
        )

        if tag == "li":
            return f"\n\n- {inner.strip()}" if inner.strip() else ""

        # Block-рівневі діти всередині inline-обходу (типово: <p>/<div>/
        # вкладений <blockquote> у <blockquote>, кілька <p> у <li>).
        # Без явної межі їхній текст злипався: "outerinner", "para1para2".
        if tag in self._INLINE_BLOCK_BOUNDARY:
            if not inner.strip():
                return ""
            return f"\n\n{inner.strip()}\n\n"

        if not getattr(self.options, "preserve_inline_formatting", True):
            return inner

        if tag in ("strong", "b"):
            return self._emphasis(inner, "**")
        if tag in ("em", "i"):
            return self._emphasis(inner, "*")
        if tag == "code":
            return self._inline_code(inner)
        if tag in ("del", "s", "strike"):
            return self._emphasis(inner, "~~")
        if tag == "a" and self.options.include_links:
            href = ""
            if hasattr(node, "get"):
                href = node.get("href", "") or ""
            elif hasattr(node, "attributes"):
                attrs = node.attributes or {}
                href = attrs.get("href", "") or ""
            if href and self.options.normalize_urls and self.options.base_url:
                href = self._normalize_url(href)
            href = self._encode_url(href)
            lead, core, trail = self._split_edge_ws(inner)
            if href and core:
                self._rendered_links += 1
                if getattr(self.options, "link_style", "inline") == "reference":
                    self._ref_counter += 1
                    ref_id = self._ref_counter
                    self._link_refs.append({"id": ref_id, "url": href})
                    return f"{lead}[{core}][{ref_id}]{trail}"
                return f"{lead}[{core}]({href}){trail}"
            return inner
        return inner

    def _finalize_inline(self, result: str) -> str:
        """Фінальна нормалізація inline-markdown: unescape, nbsp→space,
        збереження hard-break через placeholder, схлопування пробілів і
        3+ переносів (якщо не ``preserve_whitespace``).
        """
        ns = getattr(self.options, "newline_style", "spaces") or "spaces"
        hard_break = "\\\n" if ns == "backslash" else "  \n"
        result = html.unescape(result)
        result = result.replace("\xa0", " ")
        placeholder = "\x00HARDBREAK\x00"
        result = _RE_HARDBREAK_SPACES.sub(placeholder, result)
        result = _RE_HARDBREAK_BACKSLASH.sub(placeholder, result)
        preserve_ws = getattr(self.options, "preserve_whitespace", False)
        if not preserve_ws:
            result = _RE_SPACES.sub(" ", result)
            result = _RE_NEWLINES.sub("\n\n", result)
        result = result.replace(placeholder, hard_break)
        return result.strip() if not preserve_ws else result

    def _normalize_url(self, href: str) -> str:
        """Нормалізує URL (конвертує відносні в абсолютні).

        Якщо ``options.clean_urls`` увімкнено — фінальний http(s)-URL
        додатково проганяється через ``courlan.clean_url`` (прибирає
        UTM/tracker-хвости).
        """
        if not href or not self.options.base_url:
            return href

        clean = getattr(self.options, "clean_urls", False)

        if href.startswith(("http://", "https://", "mailto:", "tel:", "javascript:", "#")):
            return self._clean_url(href) if clean else href

        absolute = urljoin(self.options.base_url, href)
        return self._clean_url(absolute) if clean else absolute

    @staticmethod
    def _clean_url(url: str) -> str:
        """Прибирає UTM/tracker-параметри з http(s)-URL через courlan.

        Не-http(s) (mailto/tel/#/js) повертаються як є. courlan — опційно:
        якщо не встановлено або кинув помилку, повертаємо вхід без змін.
        """
        if not url.startswith(("http://", "https://")):
            return url
        try:
            from courlan import clean_url
        except ImportError:
            return url
        try:
            return clean_url(url) or url
        except Exception:
            return url

    def _calculate_text_density(self, element: HTMLElement, text_len: int | None = None) -> float:
        """Щільність тексту: ``len(text) / len(html)`` (вищий → більше корисного контенту)."""
        text_len = len(element.get_text(strip=True)) if text_len is None else text_len
        html_len = len(element.get_html())

        if html_len == 0:
            return 0.0

        return text_len / html_len

    def _calculate_link_density(self, element: HTMLElement, text_len: int | None = None) -> float:
        """Щільність посилань: ``link_chars / total_chars`` (меню/футер ≈ 1.0, стаття < 0.3).

        Порожній елемент → 1.0 (fallback-логіка його відкине).
        """
        text_len = len(element.get_text(strip=True)) if text_len is None else text_len
        if text_len == 0:
            # Порожній блок — трактуємо як «повністю посилання», щоб
            # fallback логіка його відкинула (безпечний default).
            return 1.0

        link_chars = 0
        for anchor in element.find_children(["a"], recursive=True):
            link_chars += len(anchor.get_text(strip=True))

        # clamp в [0, 1] — на випадок, коли text_len якось менше сумарного
        # (такого не має бути, але страхуємося).
        density = link_chars / text_len
        return density if density <= 1.0 else 1.0

    def _find_main_content(self, adapter: BaseHTMLAdapter, root: HTMLElement) -> HTMLElement:
        """Знаходить основний контент за аналізом щільності тексту.

        score = text_density * text_length зі штрафом за link_density.
        Кандидати з link_density вище ``options.link_density_threshold``
        відкидаються як навігація/футер. Повертає ``root``, якщо кандидатів немає.
        """
        candidates = []

        # Пріоритетні теги для основного контенту
        priority_tags = ["article", "main", "div", "section"]

        link_density_threshold = getattr(self.options, "link_density_threshold", 0.5)
        min_length = getattr(self.options, "main_content_min_length", 200)
        semantic_bonus = getattr(self.options, "main_content_semantic_bonus", 1.5)
        noise_penalty = getattr(self.options, "main_content_noise_penalty", 0.3)

        for element in root.iter_descendants():
            tag_name = element.tag_name.lower()

            # Розглядаємо тільки потенційні контейнери контенту
            if tag_name not in priority_tags:
                continue

            text = element.get_text(strip=True)
            text_length = len(text)

            # Пропускаємо елементи з малою кількістю тексту
            if text_length < min_length:
                continue

            # Обчислюємо link_density; викидаємо навігацію.
            # text_length передається далі, щоб _calculate_link_density і
            # _calculate_text_density не рахували get_text() повторно по
            # тому самому піддереву (3 проходи → 1).
            link_density = self._calculate_link_density(element, text_len=text_length)
            if link_density > link_density_threshold:
                continue

            # Обчислюємо щільність тексту
            density = self._calculate_text_density(element, text_len=text_length)

            # Score = density * text_length * (1 - link_density)
            # Штраф за посилання: стаття з 80% звичайного тексту і 20%
            # посилань отримує множник 0.8; пусте меню (якщо не відкинуте
            # порогом) — близький до 0.
            score = density * text_length * (1.0 - link_density)

            # Бонус для семантичних тегів
            if tag_name in ("article", "main"):
                score *= semantic_bonus

            # Перевіряємо класи та ID на noise
            class_attr = element.get_attribute("class", "")
            id_attr = element.get_attribute("id", "")

            # Зменшуємо score якщо має noise класи
            if self.options.should_remove_by_class(class_attr):
                score *= noise_penalty

            if self.options.should_remove_by_id(id_attr):
                score *= noise_penalty

            candidates.append((score, element, text_length))

        if not candidates:
            return root

        # Сортуємо за score (від найвищого)
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Повертаємо елемент з найвищим score
        return candidates[0][1]
