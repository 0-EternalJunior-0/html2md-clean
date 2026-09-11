"""Реалізація ``MarkdownGenerator``: HTML → Markdown через BS4 або Selectolax.

Selectolax використовується автоматично, якщо встановлений; інакше — BS4.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Union

from bs4 import BeautifulSoup

from markdown.adapters import BeautifulSoupAdapter, SelectolaxAdapter
from markdown.converter import UnifiedMarkdownConverter
from markdown.options import HIDDEN_CSS_CLASSES, MarkdownOptions
from markdown.result import MarkdownResult

logger = logging.getLogger(__name__)


_selectolax_available = False
try:
    from selectolax.parser import HTMLParser as SelectolaxParser

    _selectolax_available = True
except ImportError:
    SelectolaxParser = None


class MarkdownGenerator:
    """Генератор Markdown з HTML з підтримкою BS4 та Selectolax."""

    __slots__ = ("options",)

    def __init__(self, options: MarkdownOptions | None = None):
        self.options = options or MarkdownOptions()

    def _use_selectolax(self) -> bool:
        """Чи використовувати selectolax (читає опцію живим, не кешує)."""
        return _selectolax_available and not self.options.force_beautifulsoup

    @staticmethod
    def quick_generate(html: str) -> MarkdownResult:
        """Швидка генерація з дефолтними опціями."""
        return MarkdownGenerator().generate_from_html(html)

    def generate(self, source: Union[str, Any]) -> MarkdownResult:
        """Універсальний вхід: HTML-рядок або adapter."""
        if isinstance(source, str):
            return self.generate_from_html(source)

        if isinstance(source, (BeautifulSoupAdapter, SelectolaxAdapter)):
            return self.generate_from_adapter(source)

        if hasattr(source, "tree") and hasattr(source, "find_all"):
            return self.generate_from_adapter(source)

        logger.warning("Unknown source type: %s", type(source))
        return MarkdownResult.empty()

    def generate_from_html(self, html: str) -> MarkdownResult:
        """Основний вхід: HTML-рядок → ``MarkdownResult``."""
        if not html or not html.strip():
            return MarkdownResult.empty()

        # Оригінал до ftfy/trafilatura — потрібен для витягу дат
        # з meta/JSON-LD у <head>.
        source_html = html

        if getattr(self.options, "fix_text_encoding", False):
            html = self._fix_text_encoding(html)

        # Опційна санітизація перед парсингом (див. options.sanitize_html).
        if getattr(self.options, "sanitize_html", False):
            html = self._sanitize_html(html)
            if not html.strip():
                return MarkdownResult.empty()

        # Коли trafilatura успішно вилучає основний контент — свій noise-pass
        # пропускаємо, щоб не вирізати легітимний контент двічі.
        skip_noise = False
        if getattr(self.options, "use_trafilatura_extraction", False):
            extracted = self._trafilatura_preprocess(html)
            if extracted:
                html = extracted
                skip_noise = True

        try:
            if self._use_selectolax():
                result = self._process_selectolax(html, skip_noise=skip_noise)
            else:
                result = self._process_beautifulsoup(html, skip_noise=skip_noise)
        except (ValueError, AttributeError, TypeError) as e:
            logger.error("Error generating markdown: %s", e)
            return MarkdownResult.empty()

        # Опційний витяг дат виконується на ОРИГІНАЛЬНОМУ html
        # (до noise-removal), бо meta/JSON-LD часто живуть у <head>.
        if getattr(self.options, "extract_dates", False):
            published, updated = self._extract_dates(source_html)
            result.published_date = published
            result.updated_date = updated

        return result

    def _extract_dates(self, html: str) -> tuple[str | None, str | None]:
        """Витягує (published_date, updated_date) через htmldate.

        Lazy-import з graceful degradation: якщо пакета немає або парсинг
        не вдався — повертає ``(None, None)``, конвертація не переривається.
        """
        try:
            from htmldate import find_date
        except ImportError:
            logger.warning("htmldate not installed; extract_dates ignored")
            return None, None

        extensive = getattr(self.options, "extract_dates_extensive", False)
        outputformat = getattr(self.options, "date_output_format", "%Y-%m-%d")

        def _find(original: bool) -> str | None:
            try:
                return find_date(
                    html,
                    original_date=original,
                    extensive_search=extensive,
                    outputformat=outputformat,
                )
            except Exception as e:
                logger.warning("htmldate.find_date failed: %s", e)
                return None

        # original_date=True → найраніша (публікація); False → найсвіжіша (оновлення).
        return _find(True), _find(False)

    @staticmethod
    def _sanitize_html(html: str) -> str:
        """Санітизує HTML через nh3 (Rust/ammonia); graceful degradation.

        Вирізає ``<script>``/``<style>``, ``on*``-обробники та
        ``javascript:``-URL. Якщо пакета немає або виклик впав — повертає
        вхідний HTML без змін (конвертація не переривається).
        """
        try:
            import nh3
        except ImportError:
            logger.warning("nh3 not installed; sanitize_html ignored")
            return html
        try:
            return nh3.clean(html)
        except Exception as e:
            logger.warning("nh3.clean failed: %s", e)
            return html

    @staticmethod
    def _fix_text_encoding(html: str) -> str:
        """Виправляє mojibake через ftfy; graceful degradation якщо пакет відсутній."""
        try:
            import ftfy
        except ImportError:
            logger.warning("ftfy not installed; fix_text_encoding ignored")
            return html
        try:
            return ftfy.fix_text(html)
        except Exception as e:
            logger.warning("ftfy.fix_text failed: %s", e)
            return html

    @staticmethod
    def _trafilatura_preprocess(html: str) -> str:
        """Витягує основний контент через trafilatura.extract (output_format='html')."""
        try:
            import trafilatura
        except ImportError:
            logger.warning("trafilatura not installed, skipping extraction")
            return ""

        try:
            result = trafilatura.extract(
                html,
                output_format="html",
                include_links=True,
                include_images=True,
                include_tables=True,
            )
            return result or ""
        except Exception as e:
            logger.warning("trafilatura extraction failed: %s", e)
            return ""

    def _process_beautifulsoup(self, html: str, skip_noise: bool = False) -> MarkdownResult:
        """Парсить HTML через BeautifulSoup і будує ``MarkdownResult``."""
        try:
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            soup = BeautifulSoup(html, "html.parser")

        return self._convert_bs4_soup(soup, html, skip_noise=skip_noise)

    def _convert_bs4_soup(self, soup, raw_html: str, skip_noise: bool = False) -> MarkdownResult:
        """Конвертує спарсений BS4-soup у ``MarkdownResult`` (in-place очищення)."""
        converter = UnifiedMarkdownConverter(self.options)

        title = self._extract_title(soup)
        h1 = self._extract_h1(soup)
        description = self._extract_description(soup)

        if not skip_noise:
            self._remove_noise_optimized(soup)

        clean_adapter = BeautifulSoupAdapter(soup)
        fit_markdown, stats = converter.convert(clean_adapter)

        text = self._extract_text(soup)

        text = self._apply_dynamic_patterns(text)
        fit_markdown = self._apply_dynamic_patterns(fit_markdown, preserve_newlines=True)

        if self.options.normalize_unicode:
            fit_markdown = unicodedata.normalize("NFKC", fit_markdown)

        is_truncated = False
        if len(text) > self.options.max_length:
            text = self._truncate_at_word(text, self.options.max_length)
            is_truncated = True
        if len(fit_markdown) > self.options.max_length:
            fit_markdown = self._truncate_at_word(fit_markdown, self.options.max_length)
            is_truncated = True

        md_citations = ""
        references = []
        if self.options.generate_citations:
            md_citations, references = self._generate_citations_from_clean(soup)
            if len(md_citations) > self.options.max_length:
                md_citations = self._truncate_at_word(md_citations, self.options.max_length)

        result = MarkdownResult(
            text=text,
            fit_markdown=fit_markdown,
            markdown_with_citations=md_citations,
            references=references,
            title=title,
            h1=h1,
            description=description,
            word_count=len(text.split()),
            char_count=len(text),
            heading_count=stats.get("headings", 0),
            link_count=stats.get("links", 0),
            rendered_link_count=stats.get("rendered_links", 0),
            image_count=stats.get("images", 0),
            is_truncated=is_truncated,
        )

        result.set_lazy_raw_markdown(raw_html, self)

        return result

    def _process_selectolax(self, html: str, skip_noise: bool = False) -> MarkdownResult:
        """Парсить HTML через Selectolax; при помилці фолбек на BeautifulSoup."""
        try:
            tree = SelectolaxParser(html)
            return self._convert_selectolax_tree(tree, html, skip_noise=skip_noise)
        except Exception as e:
            logger.warning("Selectolax failed, falling back to BeautifulSoup: %s", e)
            return self._process_beautifulsoup(html, skip_noise=skip_noise)

    def _convert_selectolax_tree(self, tree, raw_html: str, skip_noise: bool = False) -> MarkdownResult:
        """Конвертує спарсене selectolax-дерево у ``MarkdownResult`` (in-place)."""
        converter = UnifiedMarkdownConverter(self.options)

        title = self._extract_title_selectolax(tree)
        h1 = self._extract_h1_selectolax(tree)
        description = self._extract_description_selectolax(tree)

        # Клон дерева ДО видалення шуму — використовується для лінивого
        # raw_markdown замість повторного парсингу HTML-рядка.
        raw_snapshot = None
        try:
            raw_snapshot = tree.clone()
        except Exception:
            raw_snapshot = None

        if not skip_noise:
            self._remove_noise_selectolax(tree)

        clean_adapter = SelectolaxAdapter(tree)
        fit_markdown, stats = converter.convert(clean_adapter)

        text = self._extract_text_selectolax(tree)

        text = self._apply_dynamic_patterns(text)
        fit_markdown = self._apply_dynamic_patterns(fit_markdown, preserve_newlines=True)

        if self.options.normalize_unicode:
            fit_markdown = unicodedata.normalize("NFKC", fit_markdown)

        is_truncated = False
        if len(text) > self.options.max_length:
            text = self._truncate_at_word(text, self.options.max_length)
            is_truncated = True
        if len(fit_markdown) > self.options.max_length:
            fit_markdown = self._truncate_at_word(fit_markdown, self.options.max_length)
            is_truncated = True

        md_citations = ""
        references = []
        if self.options.generate_citations:
            md_citations, references = self._generate_citations_selectolax(tree)
            if len(md_citations) > self.options.max_length:
                md_citations = self._truncate_at_word(md_citations, self.options.max_length)

        result = MarkdownResult(
            text=text,
            fit_markdown=fit_markdown,
            markdown_with_citations=md_citations,
            references=references,
            title=title,
            h1=h1,
            description=description,
            word_count=len(text.split()),
            char_count=len(text),
            heading_count=stats.get("headings", 0),
            link_count=stats.get("links", 0),
            rendered_link_count=stats.get("rendered_links", 0),
            image_count=stats.get("images", 0),
            is_truncated=is_truncated,
        )

        if raw_snapshot is not None:
            result.set_lazy_raw_tree(raw_snapshot, self)
        else:
            result.set_lazy_raw_markdown(raw_html, self)

        return result

    def _generate_raw_markdown_from_tree(self, tree) -> str:
        """Генерує raw_markdown з попереднього (pre-clean) клона selectolax-дерева."""
        try:
            self._remove_scripts_only_selectolax(tree)
            adapter = SelectolaxAdapter(tree)
            converter = UnifiedMarkdownConverter(self.options)
            raw_markdown, _ = converter.convert(adapter)
            if len(raw_markdown) > self.options.max_length:
                raw_markdown = self._truncate_at_word(raw_markdown, self.options.max_length)
            return raw_markdown
        except Exception as e:
            logger.warning("raw_markdown from tree snapshot failed: %s", e)
            return ""

    def _remove_noise_selectolax(self, tree) -> None:
        """Видаляє noise-елементи з selectolax-дерева трьома проходами."""
        # Один CSS-селектор дешевший за N окремих `tree.css(tag)`.
        if self.options.remove_scripts:
            heavy_tags = list(self.options.noise_tags)
        else:
            heavy_tags = [t for t in self.options.noise_tags if t not in ("script", "style", "noscript", "template")]

        structural = []
        if self.options.remove_nav:
            structural.append("nav")
        if self.options.remove_header:
            structural.append("header")
        if self.options.remove_footer:
            structural.append("footer")
        if self.options.remove_aside:
            structural.append("aside")
        if self.options.remove_buttons:
            structural.append("button")
        if self.options.remove_forms:
            structural.append("form")

        tag_selectors = list(heavy_tags) + structural
        for tag in tag_selectors:
            for node in tree.css(tag):
                try:
                    node.decompose()
                except (ValueError, AttributeError):
                    # Вузол уже видалений разом з батьком.
                    pass

        # Приховані елементи: aria-hidden, HTML5 hidden, hidden-класи.
        # Послідовні проходи виміряно швидші за один об'єднаний селектор:
        # об'єднаний матеріалізує вкладені вузли теж, а послідовні проходи
        # спершу зносять батьків і далі працюють на меншому дереві.
        if getattr(self.options, "remove_hidden", True):
            hidden_selectors = ['[aria-hidden="true"]', "[hidden]"]
            hidden_selectors.append(", ".join(f".{c}" for c in HIDDEN_CSS_CLASSES))
            for selector in hidden_selectors:
                for node in tree.css(selector):
                    try:
                        node.decompose()
                    except (ValueError, AttributeError):
                        pass
        if getattr(self.options, "remove_display_none", False):
            for node in tree.css("[style]"):
                style = (node.attributes.get("style") or "").replace(" ", "").lower()
                if "display:none" in style or "visibility:hidden" in style:
                    node.decompose()

        # По класам/id: class-прохід уже зносить піддерева, тому id-прохід
        # отримує менший (валідний, не detached) набір вузлів.
        if self.options.remove_ads:
            heading_selectors = "h1, h2, h3, h4, h5, h6"
            for node in tree.css("[class]"):
                class_attr = node.attributes.get("class") or ""
                if not self.options.should_remove_by_class(class_attr):
                    continue
                headings = node.css(heading_selectors) if hasattr(node, "css") else []
                if headings:
                    heading_text_len = sum(len(h.text(strip=True)) for h in headings)
                    if heading_text_len >= self.options.min_heading_length:
                        continue
                text_len = len(node.text(strip=True)) if hasattr(node, "text") else 0
                if text_len > 500:
                    continue
                try:
                    node.decompose()
                except (ValueError, AttributeError):
                    pass
            for node in tree.css("[id]"):
                node_id = node.attributes.get("id", "")
                if node_id and self.options.should_remove_by_id(node_id):
                    headings = node.css(heading_selectors) if hasattr(node, "css") else []
                    if headings:
                        heading_text_len = sum(len(h.text(strip=True)) for h in headings)
                        if heading_text_len >= self.options.min_heading_length:
                            continue
                    try:
                        node.decompose()
                    except (ValueError, AttributeError):
                        pass

    def _extract_title_selectolax(self, tree) -> str:
        title_node = tree.css_first("title")
        return title_node.text(strip=True) if title_node else ""

    def _extract_h1_selectolax(self, tree) -> str:
        h1_node = tree.css_first("h1")
        return h1_node.text(strip=True) if h1_node else ""

    def _extract_description_selectolax(self, tree) -> str:
        meta = tree.css_first('meta[name="description"]')
        if meta:
            return meta.attributes.get("content") or ""
        og_meta = tree.css_first('meta[property="og:description"]')
        if og_meta:
            return og_meta.attributes.get("content") or ""
        return ""

    def _extract_text_selectolax(self, tree) -> str:
        """Витягує чистий текст з selectolax дерева.

        Selectolax `Node.text(separator=" ")` вставляє separator між усіма
        child-текстами (включно з пробілами між inline-нодами), тому для
        консистентності з BS4 (`" ".join(text.split())`) після виклику
        схлопуємо будь-які whitespace-послідовності одним пробілом.
        """
        body = tree.css_first("body") or tree.root
        if not body:
            return ""
        try:
            raw = body.text(separator=" ", strip=True)
        except TypeError:
            # Старіші версії selectolax не приймають keyword-args
            raw = body.text(deep=True, separator=" ", strip=True)
        raw = raw.replace("\xa0", " ")
        if self.options.normalize_unicode:
            raw = unicodedata.normalize("NFKC", raw)
        if self.options.normalize_whitespace:
            return " ".join(raw.split())
        return raw

    def generate_from_adapter(self, adapter: Any) -> MarkdownResult:
        """Генерує Markdown з адаптера.

        Сумісний адаптер конвертується напряму; несумісний (напр. lxml)
        серіалізується у HTML і делегується в ``generate_from_html``.
        """
        try:
            if isinstance(adapter, SelectolaxAdapter) and self._use_selectolax():
                tree = adapter.tree
                raw_html = tree.html or ""
                return self._convert_selectolax_tree(tree, raw_html)

            if isinstance(adapter, BeautifulSoupAdapter) and not self._use_selectolax():
                soup = adapter.soup
                raw_html = str(soup)
                return self._convert_bs4_soup(soup, raw_html)

            # Несумісний адаптер (lxml/невідомий) — серіалізуємо + делегуємо.
            tree = adapter.tree
            if hasattr(tree, "find_all"):  # BeautifulSoup
                html_str = str(tree)
            elif hasattr(tree, "cssselect"):  # lxml
                from lxml import html as lxml_html

                html_str = lxml_html.tostring(tree, encoding="unicode")
            else:
                text = adapter.text if hasattr(adapter, "text") else ""
                return MarkdownResult(text=text, fit_markdown=text)

            return self.generate_from_html(html_str)

        except (ValueError, AttributeError, TypeError, ImportError) as e:
            logger.error("Error generating markdown from adapter: %s", e)
            return MarkdownResult.empty()

    def _generate_raw_markdown(self, html: str) -> str:
        """Генерує raw_markdown з HTML (lazy) тим самим парсером, що й основний прохід.

        Видаляє лише scripts/styles/noscript/template, зберігає весь інший
        контент. Парсер обирається так само, як у ``generate_from_html``
        (``_use_selectolax``), щоб ``raw_markdown`` і ``fit_markdown`` не
        розходились через різні парсери.
        """
        if self._use_selectolax():
            try:
                tree = SelectolaxParser(html)
                self._remove_scripts_only_selectolax(tree)
                adapter = SelectolaxAdapter(tree)
                converter = UnifiedMarkdownConverter(self.options)
                raw_markdown, _ = converter.convert(adapter)
                if len(raw_markdown) > self.options.max_length:
                    raw_markdown = self._truncate_at_word(raw_markdown, self.options.max_length)
                return raw_markdown
            except Exception as e:
                logger.warning("Selectolax raw_markdown failed, falling back to BS4: %s", e)

        try:
            raw_soup = BeautifulSoup(html, "lxml")
        except ImportError:
            raw_soup = BeautifulSoup(html, "html.parser")

        self._remove_scripts_only(raw_soup)

        adapter = BeautifulSoupAdapter(raw_soup)
        converter = UnifiedMarkdownConverter(self.options)
        raw_markdown, _ = converter.convert(adapter)

        if len(raw_markdown) > self.options.max_length:
            raw_markdown = self._truncate_at_word(raw_markdown, self.options.max_length)

        return raw_markdown

    @staticmethod
    def _truncate_at_word(text: str, max_length: int) -> str:
        """Відрізає текст на межі слова, а не посередині."""
        if max_length <= 0 or len(text) <= max_length:
            return text
        truncated = text[:max_length]
        if text[max_length:max_length + 1] not in (" ", "\n", "\t"):
            last_space = truncated.rfind(" ")
            if last_space > max_length // 2:
                truncated = truncated[:last_space]
        return truncated.rstrip()

    def _remove_scripts_only(self, soup) -> None:
        """Видаляє лише технічні теги (script/style/noscript/template)."""
        for tag_name in ("script", "style", "noscript", "template"):
            for tag in soup.find_all(tag_name):
                tag.decompose()

    @staticmethod
    def _remove_scripts_only_selectolax(tree) -> None:
        """Видаляє лише технічні теги (scripts, styles) з selectolax-дерева.

        Для raw_markdown зберігаємо весь контент, крім скриптів/стилів.
        """
        for tag_name in ("script", "style", "noscript", "template"):
            for node in tree.css(tag_name):
                node.decompose()

    def _remove_noise_optimized(self, soup) -> None:
        """Видаляє noise-елементи з soup, групуючи за типами для мінімуму проходів."""
        # Прохід 1: Великі блоки (мають багато вкладень, видаляємо разом)
        if self.options.remove_scripts:
            heavy_tags = list(self.options.noise_tags)
        else:
            heavy_tags = [t for t in self.options.noise_tags if t not in ("script", "style", "noscript", "template")]
        for tag in soup.find_all(heavy_tags):
            tag.decompose()

        # Прохід 2: Структурні елементи (якщо опції дозволяють)
        structural = []
        if self.options.remove_nav:
            structural.append("nav")
        if self.options.remove_header:
            structural.append("header")
        if self.options.remove_footer:
            structural.append("footer")
        if self.options.remove_aside:
            structural.append("aside")
        if self.options.remove_buttons:
            structural.append("button")
        if self.options.remove_forms:
            structural.append("form")

        if structural:
            for tag in soup.find_all(structural):
                tag.decompose()

        # Прохід 2b: приховані елементи (aria-hidden, HTML5 hidden, hidden-класи)
        # Один traversal з комбінованим предикатом замість трьох.
        if getattr(self.options, "remove_hidden", True):
            def _is_hidden(tag):
                if not hasattr(tag, "get"):
                    return False
                if tag.get("aria-hidden") == "true" or tag.has_attr("hidden"):
                    return True
                classes = tag.get("class") or []
                return bool(set(classes) & HIDDEN_CSS_CLASSES)

            for tag in soup.find_all(_is_hidden):
                tag.decompose()
        if getattr(self.options, "remove_display_none", False):
            def _has_display_none(tag):
                style = (tag.get("style") or "").replace(" ", "").lower() if hasattr(tag, "get") else ""
                return "display:none" in style or "visibility:hidden" in style
            for tag in soup.find_all(_has_display_none):
                tag.decompose()

        # Прохід 3: По класам/id (один прохід з фільтром)
        if self.options.remove_ads:

            def should_remove(tag):
                if not hasattr(tag, "get") or tag.get is None:
                    return False
                try:
                    # Перевірка класів
                    classes = tag.get("class", [])
                    if classes:
                        class_set = {c.lower() for c in classes}
                        if class_set & self.options.noise_classes:
                            return True
                    # Перевірка ID (substring match)
                    tag_id = tag.get("id", "")
                    if tag_id and self.options.should_remove_by_id(tag_id):
                        return True
                except (AttributeError, TypeError):
                    return False
                return False

            heading_tags = ["h1", "h2", "h3", "h4", "h5", "h6"]

            for tag in soup.find_all(
                    lambda t: hasattr(t, "get") and (t.get("class") or t.get("id"))
            ):
                if should_remove(tag):
                    if tag.find(heading_tags):
                        heading_text_len = sum(
                            len(h.get_text(strip=True))
                            for h in tag.find_all(heading_tags)
                        )
                        if heading_text_len >= self.options.min_heading_length:
                            text_len = len(tag.get_text(strip=True))
                            if text_len > 200:
                                continue
                            continue
                    text_len = len(tag.get_text(strip=True))
                    if text_len > 500:
                        continue
                    tag.decompose()

    def _apply_dynamic_patterns(self, text: str, preserve_newlines: bool = False) -> str:
        """Видаляє текст за ``dynamic_noise_patterns``.

        ``preserve_newlines=True`` не схлопує ``\\n`` у пробіли (потрібно для
        ``fit_markdown``, інакше втрачається структура).
        """
        if not self.options.dynamic_noise_patterns:
            return text

        # Один прохід по union-regex замість N окремих re.sub:
        # O(len(text)) замість O(K * len(text)) для K патернів.
        combined = self.options.get_combined_noise_re()
        if combined is not None:
            try:
                text = combined.sub("", text)
            except re.error as e:
                logger.warning("Invalid combined regex pattern: %s", e)

        # Нормалізуємо пробіли після видалення
        if self.options.normalize_whitespace:
            if preserve_newlines:
                # Зберігаємо CommonMark hard break (`  \n`) до нормалізації
                placeholder = "\x00HARDBREAK\x00"
                text = re.sub(r" {2,}\n", placeholder, text)
                # Схлопуємо лише горизонтальні пробіли, переноси зберігаємо.
                text = re.sub(r"[ \t]+", " ", text)
                text = re.sub(r" *\n *", "\n", text)
                text = re.sub(r"\n{3,}", "\n\n", text)
                text = text.replace(placeholder, "  \n")
                return text.strip()
            return " ".join(text.split())
        return text

    def _extract_text(self, soup) -> str:
        raw = soup.get_text(separator=" ", strip=True)

        if self.options.normalize_whitespace:
            raw = raw.replace("\xa0", " ")
            if self.options.normalize_unicode:
                raw = unicodedata.normalize("NFKC", raw)
            return " ".join(raw.split())
        if self.options.normalize_unicode:
            raw = unicodedata.normalize("NFKC", raw)
        return raw

    def _extract_title(self, soup) -> str:
        title_tag = soup.find("title")
        return title_tag.get_text(strip=True) if title_tag else ""

    def _extract_h1(self, soup) -> str:
        h1_tag = soup.find("h1")
        return h1_tag.get_text(strip=True) if h1_tag else ""

    def _extract_description(self, soup) -> str:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            return meta.get("content", "")

        # Fallback: og:description
        og_meta = soup.find("meta", attrs={"property": "og:description"})
        if og_meta:
            return og_meta.get("content", "")

        return ""

    def _generate_citations_from_clean(self, soup) -> tuple[str, list[dict[str, str]]]:
        """Генерує citations з вже очищеного soup (без додаткового парсингу)."""
        import copy
        citations_soup = copy.copy(soup)
        return self._generate_citations(citations_soup)

    def _generate_citations(self, soup) -> tuple[str, list[dict[str, str]]]:
        """Генерує Markdown з citations ``[1]``, ``[2]`` на копії soup (оригінал не чіпає)."""
        references = []
        ref_counter = 1

        converter = UnifiedMarkdownConverter(self.options)

        # Знаходимо всі посилання
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)

            if href and text and not href.startswith("#"):
                href = converter._normalize_url(href)
                references.append({"id": ref_counter,"text": text,"url": href})
                # Замінюємо посилання на citation
                a.replace_with(f"{text} [{ref_counter}]")
                ref_counter += 1

        # Генеруємо markdown через UnifiedConverter
        adapter = BeautifulSoupAdapter(soup)
        md, _ = converter.convert(adapter)

        # Додаємо references в кінці
        if references:
            md += "\n\n## References\n\n"
            for ref in references:
                md += f"[{ref['id']}] {ref['url']}\n"

        return md, references

    def _generate_citations_selectolax(self, tree) -> tuple[str, list[dict[str, str]]]:
        """Генерує Markdown з citations ``[1]``, ``[2]`` для selectolax-дерева."""
        references = []
        ref_counter = 1

        converter = UnifiedMarkdownConverter(self.options)

        for node in tree.css("a"):
            href = node.attributes.get("href", "")
            text = node.text(strip=True)
            if href and text and not href.startswith("#"):
                href = converter._normalize_url(href)
                references.append({"id": ref_counter, "text": text, "url": href})
                node.replace_with(f"{text} [{ref_counter}]")
                ref_counter += 1

        adapter = SelectolaxAdapter(tree)
        md, _ = converter.convert(adapter)

        if references:
            md += "\n\n## References\n\n"
            for ref in references:
                md += f"[{ref['id']}] {ref['url']}\n"

        return md, references


async def generate_markdown_async(html: str,options: MarkdownOptions | None = None) -> MarkdownResult:
    """Асинхронна генерація Markdown у thread executor (non-blocking)."""
    import asyncio

    generator = MarkdownGenerator(options)

    try:
        return await asyncio.to_thread(generator.generate_from_html, html)
    except AttributeError:
        # asyncio.to_thread недоступний до Python 3.9 — fallback на executor.
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            generator.generate_from_html,
            html,
        )
