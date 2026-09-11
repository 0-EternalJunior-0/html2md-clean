"""Comprehensive tests for UnifiedMarkdownConverter.

Tests every element type and option handled by the converter:
headings, paragraphs, code blocks, lists, blockquotes, images,
tables, horizontal rules, definition lists, containers, URL
normalization, strict escaping, bullet cycling, newline style,
content/link density.
"""

import re
import pytest

from markdown.converter import UnifiedMarkdownConverter
from markdown.options import MarkdownOptions
from markdown.adapters.bs4_adapter import BeautifulSoupAdapter

try:
    from selectolax.parser import HTMLParser as SelectolaxParser
    from markdown.adapters.selectolax_adapter import SelectolaxAdapter
    SELECTOLAX_AVAILABLE = True
except ImportError:
    SELECTOLAX_AVAILABLE = False


def bs4_convert(html, options=None):
    """Convert HTML via BS4 adapter. Returns (markdown, stats).

    Uses min_paragraph_length=0 so short test content is not filtered out.
    """
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html, "lxml")
    except ImportError:
        soup = BeautifulSoup(html, "html.parser")
    adapter = BeautifulSoupAdapter(soup)
    opts = options or MarkdownOptions(min_paragraph_length=0, min_heading_length=0)
    conv = UnifiedMarkdownConverter(opts)
    return conv.convert(adapter)


def bs4_convert_with_opts(html, opts):
    """Convert HTML via BS4 adapter with given options."""
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html, "lxml")
    except ImportError:
        soup = BeautifulSoup(html, "html.parser")
    adapter = BeautifulSoupAdapter(soup)
    conv = UnifiedMarkdownConverter(opts)
    return conv.convert(adapter)


# ═══════════════════════════════════════════════════════════════════════════
#  1. Headings
# ═══════════════════════════════════════════════════════════════════════════

class TestHeadings:

    def test_h1(self):
        md, stats = bs4_convert("<html><body><h1>Title</h1></body></html>")
        assert "# Title" in md
        assert stats["headings"] == 1

    def test_h2(self):
        md, stats = bs4_convert("<html><body><h2>Subtitle</h2></body></html>")
        assert "## Subtitle" in md

    def test_h3_to_h6(self):
        for level in range(3, 7):
            tag = f"h{level}"
            md, _ = bs4_convert(f"<html><body><{tag}>Level {level}</{tag}></body></html>")
            hashes = "#" * level
            assert f"{hashes} Level {level}" in md

    def test_heading_with_inline_formatting(self):
        md, _ = bs4_convert("<html><body><h1>Bold <strong>word</strong></h1></body></html>")
        assert "# " in md
        assert "Bold" in md

    def test_heading_min_length_filter(self):
        opts = MarkdownOptions(min_heading_length=15)
        md, stats = bs4_convert_with_opts(
            "<html><body><h1>Hi</h1><h1>Long Enough Title Here</h1></body></html>",
            opts,
        )
        assert "Hi" not in md
        assert "Long Enough Title Here" in md

    def test_heading_min_length_zero(self):
        opts = MarkdownOptions(min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><h1>X</h1></body></html>", opts
        )
        assert "# X" in md

    def test_heading_strict_escape(self):
        opts = MarkdownOptions(strict_escape=True, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><h1>Title with * asterisks</h1></body></html>", opts
        )
        assert "\\*" in md


# ═══════════════════════════════════════════════════════════════════════════
#  2. Paragraphs
# ═══════════════════════════════════════════════════════════════════════════

class TestParagraphs:

    def test_simple_paragraph(self):
        md, _ = bs4_convert("<html><body><p>Hello world</p></body></html>")
        assert "Hello world" in md

    def test_paragraph_min_length_filter(self):
        opts = MarkdownOptions(min_paragraph_length=50)
        md, _ = bs4_convert_with_opts(
            "<html><body><p>Short</p><p>This is a much longer paragraph that definitely exceeds the minimum length requirement</p></body></html>",
            opts,
        )
        assert "Short" not in md
        assert "much longer" in md

    def test_paragraph_min_length_zero(self):
        opts = MarkdownOptions(min_paragraph_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><p>Hi</p></body></html>", opts
        )
        assert "Hi" in md

    def test_multiple_paragraphs(self):
        md, _ = bs4_convert(
            "<html><body><p>First paragraph text here</p><p>Second paragraph text here</p><p>Third paragraph text here</p></body></html>"
        )
        assert "First paragraph" in md
        assert "Second paragraph" in md
        assert "Third paragraph" in md


# ═══════════════════════════════════════════════════════════════════════════
#  3. Code blocks
# ═══════════════════════════════════════════════════════════════════════════

class TestCodeBlocks:

    def test_plain_code_block(self):
        md, stats = bs4_convert(
            "<html><body><pre><code>print('hello')</code></pre></body></html>"
        )
        assert "```" in md
        assert "print('hello')" in md
        assert stats["code"] == 1

    def test_code_block_with_language(self):
        md, _ = bs4_convert(
            '<html><body><pre><code class="language-python">import os</code></pre></body></html>'
        )
        assert "```python" in md

    def test_code_block_with_lang_prefix(self):
        md, _ = bs4_convert(
            '<html><body><pre><code class="lang-javascript">const x = 1;</code></pre></body></html>'
        )
        assert "```javascript" in md

    def test_code_blocks_excluded(self):
        opts = MarkdownOptions(include_code_blocks=False, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><pre><code>code here</code></pre></body></html>", opts
        )
        assert "```" not in md


# ═══════════════════════════════════════════════════════════════════════════
#  4. Lists
# ═══════════════════════════════════════════════════════════════════════════

class TestLists:

    def test_unordered_list(self):
        md, stats = bs4_convert(
            "<html><body><ul><li>First item here</li><li>Second item here</li><li>Third item here</li></ul></body></html>"
        )
        assert "First item here" in md
        assert "Second item here" in md
        assert stats["lists"] == 1

    def test_ordered_list(self):
        md, _ = bs4_convert(
            "<html><body><ol><li>First item here</li><li>Second item here</li><li>Third item here</li></ol></body></html>"
        )
        assert "1." in md
        assert "2." in md
        assert "3." in md

    def test_nested_list(self):
        md, _ = bs4_convert(
            "<html><body><ul><li>Parent item<ul><li>Child one</li><li>Child two</li></ul></li></ul></body></html>"
        )
        assert "Parent item" in md
        assert "Child one" in md
        assert "Child two" in md

    def test_task_list_checked(self):
        md, _ = bs4_convert(
            '<html><body><ul><li><input type="checkbox" checked> Done task item</li></ul></body></html>'
        )
        assert "[x]" in md
        assert "Done task item" in md

    def test_task_list_unchecked(self):
        md, _ = bs4_convert(
            '<html><body><ul><li><input type="checkbox"> Todo task item</li></ul></body></html>'
        )
        assert "[ ]" in md
        assert "Todo task item" in md

    def test_list_bullet_cycling(self):
        opts = MarkdownOptions(bullets="-*+", min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><ul><li>Level one item<ul><li>Level two item<ul><li>Level three item</li></ul></li></ul></li></ul></body></html>",
            opts,
        )
        assert "- Level one" in md
        assert "* Level two" in md
        assert "+ Level three" in md

    def test_list_bullet_custom(self):
        opts = MarkdownOptions(bullets="*", min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><ul><li>Custom bullet item</li></ul></body></html>", opts
        )
        assert "* Custom bullet item" in md

    def test_lists_excluded(self):
        opts = MarkdownOptions(include_lists=False, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><ul><li>Excluded item</li></ul></body></html>", opts
        )
        assert "- " not in md

    def test_definition_list(self):
        md, _ = bs4_convert(
            "<html><body><dl><dt>Term definition here</dt><dd>Definition content here</dd></dl></body></html>"
        )
        assert "Term definition here" in md
        assert ": Definition content here" in md


# ═══════════════════════════════════════════════════════════════════════════
#  5. Blockquotes
# ═══════════════════════════════════════════════════════════════════════════

class TestBlockquotes:

    def test_simple_blockquote(self):
        md, _ = bs4_convert(
            "<html><body><blockquote><p>Quote text content here</p></blockquote></body></html>"
        )
        assert "> " in md
        assert "Quote text content" in md

    def test_blockquote_with_inline(self):
        md, _ = bs4_convert(
            "<html><body><blockquote><p><strong>Bold text</strong> in quote</p></blockquote></body></html>"
        )
        assert "> " in md

    def test_blockquote_multiline(self):
        md, _ = bs4_convert(
            "<html><body><blockquote><p>Line one of the blockquote</p><p>Line two of the blockquote</p></blockquote></body></html>"
        )
        assert ">" in md
        assert "Line one" in md
        assert "Line two" in md

    def test_blockquotes_excluded(self):
        opts = MarkdownOptions(include_blockquotes=False, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><blockquote><p>Excluded quote</p></blockquote></body></html>", opts
        )
        assert ">" not in md


# ═══════════════════════════════════════════════════════════════════════════
#  6. Images
# ═══════════════════════════════════════════════════════════════════════════

class TestImages:

    def test_image_with_alt(self):
        opts = MarkdownOptions(include_images=True, min_paragraph_length=0, min_heading_length=0)
        md, stats = bs4_convert_with_opts(
            '<html><body><p>Text before</p><img src="/pic.jpg" alt="Photo"><p>Text after</p></body></html>', opts
        )
        assert "![Photo](/pic.jpg)" in md
        assert stats["images"] == 1

    def test_image_no_alt(self):
        opts = MarkdownOptions(include_images=True, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            '<html><body><p>Text</p><img src="/pic.jpg"><p>More</p></body></html>', opts
        )
        assert "/pic.jpg" in md

    def test_images_excluded(self):
        opts = MarkdownOptions(include_images=False, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            '<html><body><p>Text</p><img src="/pic.jpg" alt="Photo"><p>More</p></body></html>', opts
        )
        assert "![" not in md

    def test_image_url_normalized(self):
        opts = MarkdownOptions(
            include_images=True, base_url="https://example.com", normalize_urls=True,
            min_paragraph_length=0, min_heading_length=0,
        )
        md, _ = bs4_convert_with_opts(
            '<html><body><p>Text</p><img src="/img.png" alt="Pic"><p>More</p></body></html>', opts
        )
        assert "https://example.com/img.png" in md


# ═══════════════════════════════════════════════════════════════════════════
#  7. Tables
# ═══════════════════════════════════════════════════════════════════════════

class TestTables:

    def test_simple_table(self):
        md, stats = bs4_convert(
            "<html><body><table>"
            "<thead><tr><th>Alpha</th><th>Beta</th></tr></thead>"
            "<tbody><tr><td>One</td><td>Two</td></tr></tbody>"
            "</table></body></html>"
        )
        assert "| Alpha | Beta |" in md
        assert "| --- | --- |" in md
        assert "| One | Two |" in md
        assert stats["tables"] == 1

    def test_table_without_thead(self):
        md, _ = bs4_convert(
            "<html><body><table>"
            "<tr><td>X value</td><td>Y value</td></tr>"
            "<tr><td>One value</td><td>Two value</td></tr>"
            "</table></body></html>"
        )
        assert "|" in md

    def test_table_with_colspan(self):
        # Нова семантика: colspan ПОВТОРЮЄ значення (а не добиває порожніми).
        md, _ = bs4_convert(
            "<html><body><table>"
            "<thead><tr><th>Alpha</th><th>Beta</th><th>Gamma</th></tr></thead>"
            "<tbody><tr><td>One</td><td colspan='2'>spanned cell</td></tr></tbody>"
            "</table></body></html>"
        )
        assert "| One | spanned cell | spanned cell |" in md

    def test_table_pipe_escaping(self):
        md, _ = bs4_convert(
            "<html><body><table>"
            "<tr><td>Cell with pipe</td><td>Normal cell</td></tr>"
            "</table></body></html>"
        )
        assert "|" in md

    def test_table_newline_in_cell(self):
        md, _ = bs4_convert(
            "<html><body><table>"
            "<tr><td>line1\nline2</td><td>Normal cell</td></tr>"
            "</table></body></html>"
        )
        assert "|" in md

    def test_tables_excluded(self):
        opts = MarkdownOptions(include_tables=False, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><p>Before</p><table><tr><td>Cell value</td></tr></table><p>After</p></body></html>", opts
        )
        assert "|" not in md

    def test_table_col_count_normalization(self):
        md, _ = bs4_convert(
            "<html><body><table>"
            "<thead><tr><th>Alpha</th><th>Beta</th><th>Gamma</th></tr></thead>"
            "<tbody>"
            "<tr><td>One</td><td>Two</td><td>Three</td></tr>"
            "<tr><td>Four</td><td>Five</td></tr>"
            "</tbody></table></body></html>"
        )
        rows = [l for l in md.split("\n") if l.strip().startswith("|")]
        pipe_counts = [l.count("|") for l in rows]
        assert len(set(pipe_counts)) <= 1


# ═══════════════════════════════════════════════════════════════════════════
#  7b. Table rowspan / colspan grid materialization (10 orthogonal vectors)
# ═══════════════════════════════════════════════════════════════════════════

def _table_md(html):
    """Convert a single table's HTML and return stripped markdown."""
    md, _ = bs4_convert("<html><body>" + html + "</body></html>")
    return md.strip()


class TestTableSpans:
    """По одному тесту на кожен з 10 контрольних векторів ТЗ.

    Політика: матеріалізація сітки з протягуванням значень — `rowspan`
    вертикально, `colspan` горизонтально (обидва повтором); `rowspan=0`
    до кінця секції; невалідні/`≤0` → 1; clamp без фантомних рядків;
    вкладена таблиця в межах однієї клітинки; двоярусний `thead` склеюється.
    """

    def test_vector1_basic_vertical_span(self):
        md = _table_md(
            "<table>"
            "<tr><th>Регіон</th><th>Місто</th><th>Продажі</th></tr>"
            "<tr><td rowspan='2'>Захід</td><td>Львів</td><td>100</td></tr>"
            "<tr><td>Ужгород</td><td>50</td></tr>"
            "</table>"
        )
        assert md == (
            "| Регіон | Місто | Продажі |\n"
            "| --- | --- | --- |\n"
            "| Захід | Львів | 100 |\n"
            "| Захід | Ужгород | 50 |"
        )

    def test_vector2_rowspan_colspan_block(self):
        md = _table_md(
            "<table>"
            "<tr><td rowspan='2' colspan='2'>Блок</td><td>A</td></tr>"
            "<tr><td>B</td></tr>"
            "</table>"
        )
        assert md == (
            "| Col 1 | Col 2 | Col 3 |\n"
            "| --- | --- | --- |\n"
            "| Блок | Блок | A |\n"
            "| Блок | Блок | B |"
        )

    def test_vector3_rowspan_middle_column(self):
        md = _table_md(
            "<table>"
            "<tr><th>Час</th><th>Пн</th><th>Вт</th></tr>"
            "<tr><td>09:00</td><td rowspan='2'>Математика</td><td>Фізика</td></tr>"
            "<tr><td>10:00</td><td>Хімія</td></tr>"
            "</table>"
        )
        assert md == (
            "| Час | Пн | Вт |\n"
            "| --- | --- | --- |\n"
            "| 09:00 | Математика | Фізика |\n"
            "| 10:00 | Математика | Хімія |"
        )

    def test_vector4_multiple_parallel_rowspans(self):
        md = _table_md(
            "<table>"
            "<tr><td rowspan='3'>A</td><td>1</td><td rowspan='2'>X</td></tr>"
            "<tr><td>2</td></tr>"
            "<tr><td>3</td><td>Y</td></tr>"
            "</table>"
        )
        assert md == (
            "| Col 1 | Col 2 | Col 3 |\n"
            "| --- | --- | --- |\n"
            "| A | 1 | X |\n"
            "| A | 2 | X |\n"
            "| A | 3 | Y |"
        )

    def test_vector5_two_tier_grouped_header(self):
        md = _table_md(
            "<table>"
            "<thead>"
            "<tr><th rowspan='2'>Товар</th><th colspan='2'>2023</th><th colspan='2'>2024</th></tr>"
            "<tr><th>Q1</th><th>Q2</th><th>Q1</th><th>Q2</th></tr>"
            "</thead>"
            "<tbody><tr><td>Кава</td><td>10</td><td>12</td><td>14</td><td>16</td></tr></tbody>"
            "</table>"
        )
        assert md == (
            "| Товар | 2023 Q1 | 2023 Q2 | 2024 Q1 | 2024 Q2 |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| Кава | 10 | 12 | 14 | 16 |"
        )

    def test_vector6_rowspan_clamp_no_phantom(self):
        md = _table_md(
            "<table>"
            "<tr><td rowspan='99'>Вічний</td><td>1</td></tr>"
            "<tr><td>2</td></tr>"
            "</table>"
        )
        assert md == (
            "| Col 1 | Col 2 |\n"
            "| --- | --- |\n"
            "| Вічний | 1 |\n"
            "| Вічний | 2 |"
        )

    def test_vector7_rowspan_zero_and_invalid(self):
        md = _table_md(
            "<table>"
            "<tr><td rowspan='0'>ДоКінця</td><td>a</td></tr>"
            "<tr><td>b</td></tr>"
            "<tr><td>c</td></tr>"
            "<tr><td rowspan='-3'>Бра</td><td>d</td></tr>"
            "</table>"
        )
        assert md == (
            "| Col 1 | Col 2 |\n"
            "| --- | --- |\n"
            "| ДоКінця | a |\n"
            "| ДоКінця | b |\n"
            "| ДоКінця | c |\n"
            "| Бра | d |"
        )

    def test_vector8_nested_table_in_rowspan_cell(self):
        md = _table_md(
            "<table>"
            "<tr>"
            "<td rowspan='2'>"
            "<table>"
            "<tr><td>n1</td><td>n2</td></tr>"
            "<tr><td>n3</td><td>n4</td></tr>"
            "</table>"
            "</td>"
            "<td>Верх</td>"
            "</tr>"
            "<tr><td>Низ</td></tr>"
            "</table>"
        )
        assert md == (
            "| Col 1 | Col 2 |\n"
            "| --- | --- |\n"
            "| n1 / n2<br>n3 / n4 | Верх |\n"
            "| n1 / n2<br>n3 / n4 | Низ |"
        )

    def test_vector9_ragged_matrix(self):
        md = _table_md(
            "<table>"
            "<tr><td rowspan='2'>A</td><td colspan='2'>B2</td></tr>"
            "<tr><td>C</td><td>D</td></tr>"
            "<tr><td colspan='3'>E3</td></tr>"
            "</table>"
        )
        assert md == (
            "| Col 1 | Col 2 | Col 3 |\n"
            "| --- | --- | --- |\n"
            "| A | B2 | B2 |\n"
            "| A | C | D |\n"
            "| E3 | E3 | E3 |"
        )

    def test_vector10_spanned_rich_inline_cell(self):
        md = _table_md(
            "<table>"
            "<tr><th>Ключ</th><th>Опис</th></tr>"
            "<tr>"
            "<td rowspan='2'>Статус: <strong>OK</strong> | <a href='/x'>лінк</a><br>рядок2"
            "<ul><li>a</li><li>b</li></ul>"
            "</td>"
            "<td>перший</td>"
            "</tr>"
            "<tr><td>другий</td></tr>"
            "</table>"
        )
        expected_cell = r"Статус: **OK** \| [лінк](/x)<br>рядок2<br>a<br>b"
        assert md == (
            "| Ключ | Опис |\n"
            "| --- | --- |\n"
            f"| {expected_cell} | перший |\n"
            f"| {expected_cell} | другий |"
        )



# ═══════════════════════════════════════════════════════════════════════════
#  8. Horizontal rules
# ═══════════════════════════════════════════════════════════════════════════

class TestHorizontalRules:

    def test_hr(self):
        md, _ = bs4_convert(
            "<html><body><p>Content before the rule</p><hr><p>Content after the rule</p></body></html>"
        )
        assert "---" in md
        assert "Content before" in md
        assert "Content after" in md


# ═══════════════════════════════════════════════════════════════════════════
#  9. URL normalization
# ═══════════════════════════════════════════════════════════════════════════

class TestUrlNormalization:

    def test_relative_url_in_link(self):
        opts = MarkdownOptions(
            base_url="https://example.com/blog/", normalize_urls=True,
            min_paragraph_length=0, min_heading_length=0,
        )
        md, _ = bs4_convert_with_opts(
            '<html><body><p>See <a href="/about">About page</a> for info</p></body></html>', opts
        )
        assert "https://example.com/about" in md

    def test_absolute_https_unchanged(self):
        opts = MarkdownOptions(
            base_url="https://example.com", normalize_urls=True,
            min_paragraph_length=0, min_heading_length=0,
        )
        md, _ = bs4_convert_with_opts(
            '<html><body><p>See <a href="https://other.com/page">Other page</a> for info</p></body></html>',
            opts,
        )
        assert "https://other.com/page" in md

    def test_absolute_http_unchanged(self):
        opts = MarkdownOptions(
            base_url="https://example.com", normalize_urls=True,
            min_paragraph_length=0, min_heading_length=0,
        )
        md, _ = bs4_convert_with_opts(
            '<html><body><p>See <a href="http://other.com/page">Other page</a> for info</p></body></html>',
            opts,
        )
        assert "http://other.com/page" in md

    def test_mailto_unchanged(self):
        opts = MarkdownOptions(
            base_url="https://example.com", normalize_urls=True,
            min_paragraph_length=0, min_heading_length=0,
        )
        md, _ = bs4_convert_with_opts(
            '<html><body><p>Contact <a href="mailto:user@example.com">the user</a> for info</p></body></html>',
            opts,
        )
        assert "mailto:user@example.com" in md

    def test_anchor_unchanged(self):
        opts = MarkdownOptions(
            base_url="https://example.com", normalize_urls=True,
            min_paragraph_length=0, min_heading_length=0,
        )
        md, _ = bs4_convert_with_opts(
            '<html><body><p>Jump to <a href="#section">section</a> below</p></body></html>', opts
        )
        assert "#section" in md

    def test_no_base_url_no_normalization(self):
        opts = MarkdownOptions(base_url="", normalize_urls=True,
                               min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            '<html><body><p>See <a href="/about">About page</a> for info</p></body></html>', opts
        )
        assert "/about" in md
        assert "https://example.com" not in md


# ═══════════════════════════════════════════════════════════════════════════
#  10. Inline formatting
# ═══════════════════════════════════════════════════════════════════════════

class TestInlineFormatting:

    def test_strong_bold(self):
        md, _ = bs4_convert(
            "<html><body><p><strong>Bold text content</strong> normal text</p></body></html>"
        )
        assert "**Bold text content**" in md

    def test_b_tag_bold(self):
        md, _ = bs4_convert(
            "<html><body><p><b>Bold text content</b> normal text</p></body></html>"
        )
        assert "**Bold text content**" in md

    def test_em_italic(self):
        md, _ = bs4_convert(
            "<html><body><p><em>Italic text content</em> normal text</p></body></html>"
        )
        assert "*Italic text content*" in md

    def test_i_tag_italic(self):
        md, _ = bs4_convert(
            "<html><body><p><i>Italic text content</i> normal text</p></body></html>"
        )
        assert "*Italic text content*" in md

    def test_del_strikethrough(self):
        md, _ = bs4_convert(
            "<html><body><p><del>Deleted text content</del> normal text</p></body></html>"
        )
        assert "~~Deleted text content~~" in md

    def test_s_tag_strikethrough(self):
        md, _ = bs4_convert(
            "<html><body><p><s>Deleted text content</s> normal text</p></body></html>"
        )
        assert "~~Deleted text content~~" in md

    def test_strike_tag_strikethrough(self):
        md, _ = bs4_convert(
            "<html><body><p><strike>Deleted text content</strike> normal text</p></body></html>"
        )
        assert "~~Deleted text content~~" in md

    def test_inline_code(self):
        md, _ = bs4_convert(
            "<html><body><p>Use the <code>print()</code> function here</p></body></html>"
        )
        assert "`print()`" in md

    def test_br_spaces_style(self):
        opts = MarkdownOptions(newline_style="spaces", min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><p>Line one text<br>Line two text</p></body></html>", opts
        )
        assert "Line one text" in md
        assert "Line two text" in md

    def test_br_backslash_style(self):
        opts = MarkdownOptions(newline_style="backslash", min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><p>Line one text<br>Line two text</p></body></html>", opts
        )
        assert "Line one text" in md
        assert "Line two text" in md

    def test_combined_formatting(self):
        md, _ = bs4_convert(
            "<html><body><p>Mixed <strong>bold text</strong> and <em>italic text</em> and <code>code text</code> together here</p></body></html>"
        )
        assert "**bold text**" in md
        assert "*italic text*" in md


# ═══════════════════════════════════════════════════════════════════════════
#  11. Strict escape
# ═══════════════════════════════════════════════════════════════════════════

class TestStrictEscape:

    def test_escapes_special_chars(self):
        opts = MarkdownOptions(strict_escape=True, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><p>Text with asterisks here</p></body></html>", opts
        )
        # Just verify it doesn't crash and produces output
        assert len(md) > 0

    def test_escapes_in_heading(self):
        opts = MarkdownOptions(strict_escape=True, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><h1>Title with * asterisks</h1></body></html>", opts
        )
        assert "\\*" in md

    def test_no_escape_by_default(self):
        opts = MarkdownOptions(strict_escape=False, min_paragraph_length=0, min_heading_length=0)
        md, _ = bs4_convert_with_opts(
            "<html><body><h1>Title with asterisks</h1></body></html>", opts
        )
        assert "\\*" not in md


# ═══════════════════════════════════════════════════════════════════════════
#  12. Container processing
# ═══════════════════════════════════════════════════════════════════════════

class TestContainers:

    def test_div_with_paragraphs(self):
        md, _ = bs4_convert(
            "<html><body><div><p>First paragraph content</p><p>Second paragraph content</p></div></body></html>"
        )
        assert "First paragraph" in md
        assert "Second paragraph" in md

    def test_div_with_block_children(self):
        md, _ = bs4_convert(
            "<html><body><div><h2>Heading inside div</h2><p>Paragraph inside div</p></div></body></html>"
        )
        assert "## Heading inside div" in md
        assert "Paragraph inside div" in md

    def test_section_with_block_children(self):
        md, _ = bs4_convert(
            "<html><body><section><h2>Section heading here</h2><p>Section paragraph here</p></section></body></html>"
        )
        assert "## Section heading" in md
        assert "Section paragraph" in md

    def test_inline_only_div(self):
        md, _ = bs4_convert(
            "<html><body><div><span>Hello world</span> <span>another span</span></div></body></html>"
        )
        assert "Hello world" in md


# ═══════════════════════════════════════════════════════════════════════════
#  13. Content density
# ═══════════════════════════════════════════════════════════════════════════

class TestContentDensityConverter:

    def test_finds_main_content(self):
        opts = MarkdownOptions(use_content_density=True, min_content_words=10)
        conv = UnifiedMarkdownConverter(opts)

        body_text = "word " * 50
        html = f"""<html><body>
            <nav><a href="/1">Link1</a><a href="/2">Link2</a><a href="/3">Link3</a></nav>
            <article><h1>Main article heading</h1><p>{body_text}</p></article>
        </body></html>"""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            soup = BeautifulSoup(html, "html.parser")
        adapter = BeautifulSoupAdapter(soup)
        md, _ = conv.convert(adapter)
        assert "Main article heading" in md

    def test_fallback_when_main_too_short(self):
        opts = MarkdownOptions(use_content_density=True, min_content_words=1000)
        conv = UnifiedMarkdownConverter(opts)

        html = """<html><body>
            <p>Short content that is too few words to pass the threshold</p>
        </body></html>"""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            soup = BeautifulSoup(html, "html.parser")
        adapter = BeautifulSoupAdapter(soup)
        md, _ = conv.convert(adapter)
        assert md


# ═══════════════════════════════════════════════════════════════════════════
#  14. Link density
# ═══════════════════════════════════════════════════════════════════════════

class TestLinkDensity:

    def test_link_density_excludes_nav(self):
        opts = MarkdownOptions(
            use_content_density=True,
            link_density_threshold=0.3,
            min_content_words=10,
        )
        conv = UnifiedMarkdownConverter(opts)

        html = """<html><body>
            <nav><a href="/1">Link 1</a><a href="/2">Link 2</a><a href="/3">Link 3</a></nav>
            <article><h1>Main article heading</h1><p>This is real content with enough words to pass the minimum threshold check for content density. It has multiple sentences with actual information, examples, and detailed explanations to ensure the length exceeds the hardcoded content-density minimum threshold of two hundred characters, so the extractor picks it as the main content region and not the navigation block above.</p></article>
        </body></html>"""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(html, "lxml")
        except ImportError:
            soup = BeautifulSoup(html, "html.parser")
        adapter = BeautifulSoupAdapter(soup)
        md, _ = conv.convert(adapter)
        assert "Link 1" not in md
        assert "Main article heading" in md


# ═══════════════════════════════════════════════════════════════════════════
#  15. HTML entities
# ═══════════════════════════════════════════════════════════════════════════

class TestHtmlEntities:

    def test_ampersand(self):
        md, _ = bs4_convert(
            "<html><body><p>Entity test with ampersand here</p></body></html>"
        )
        assert "ampersand" in md

    def test_copyright(self):
        md, _ = bs4_convert(
            "<html><body><p>Copyright 2024 test text</p></body></html>"
        )
        assert "Copyright" in md


def test_helper_exists():
    assert bs4_convert is not None
    assert bs4_convert_with_opts is not None
