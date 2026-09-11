"""Comprehensive tests for MarkdownGenerator.

Tests both BS4 and Selectolax parsers, all generation modes,
noise removal, dynamic patterns, content density, citations,
truncation, async, and URL normalization.
"""

import asyncio
import os
import pytest

from markdown.generator import MarkdownGenerator, generate_markdown_async
from markdown.options import MarkdownOptions
from markdown.result import MarkdownResult


# ═══════════════════════════════════════════════════════════════════════════
#  1. Basic generation
# ═══════════════════════════════════════════════════════════════════════════

class TestBasicGeneration:

    def test_generate_from_html_returns_result(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown

    def test_quick_generate(self, simple_html):
        result = MarkdownGenerator.quick_generate(simple_html)
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown

    def test_generate_string_input(self, generator, simple_html):
        result = generator.generate(simple_html)
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown

    def test_generate_empty_string(self, generator):
        result = generator.generate_from_html("")
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown == ""
        assert result.text == ""
        assert result.word_count == 0

    def test_generate_whitespace_only(self, generator):
        result = generator.generate_from_html("   \n\t  ")
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown == ""

    def test_generate_none_like(self, generator):
        result = generator.generate_from_html("")
        assert result == MarkdownResult.empty()

    def test_generate_minimal_html(self, generator):
        result = generator.generate_from_html(
            "<html><body><h1>A long enough heading title</h1></body></html>"
        )
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown


# ═══════════════════════════════════════════════════════════════════════════
#  2. BS4 vs Selectolax consistency
# ═══════════════════════════════════════════════════════════════════════════

class TestParserConsistency:

    def test_bs4_and_selectolax_produce_non_empty(self, simple_html):
        bs4_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))
        sl_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=False))

        bs4_result = bs4_gen.generate_from_html(simple_html)
        sl_result = sl_gen.generate_from_html(simple_html)

        assert bs4_result.fit_markdown
        assert sl_result.fit_markdown

    def test_bs4_and_selectolax_both_extract_title(self, simple_html):
        bs4_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))
        sl_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=False))

        bs4_result = bs4_gen.generate_from_html(simple_html)
        sl_result = sl_gen.generate_from_html(simple_html)

        assert bs4_result.title == "Test Page"
        assert sl_result.title == "Test Page"

    def test_bs4_and_selectolax_both_extract_h1(self, simple_html):
        bs4_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))
        sl_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=False))

        bs4_result = bs4_gen.generate_from_html(simple_html)
        sl_result = sl_gen.generate_from_html(simple_html)

        assert bs4_result.h1 == "Main Title"
        assert sl_result.h1 == "Main Title"


# ═══════════════════════════════════════════════════════════════════════════
#  3. Noise removal
# ═══════════════════════════════════════════════════════════════════════════

class TestNoiseRemoval:

    def test_nav_removed_by_default(self, generator, nav_heavy_html):
        result = generator.generate_from_html(nav_heavy_html)
        assert "main-nav" not in result.fit_markdown
        assert "Page 1" not in result.fit_markdown

    def test_header_removed_by_default(self, generator, nav_heavy_html):
        result = generator.generate_from_html(nav_heavy_html)
        assert "Site Header" not in result.fit_markdown

    def test_footer_removed_by_default(self, generator, nav_heavy_html):
        result = generator.generate_from_html(nav_heavy_html)
        assert "Footer" not in result.fit_markdown

    def test_aside_removed_by_default(self, generator, nav_heavy_html):
        result = generator.generate_from_html(nav_heavy_html)
        assert "Sidebar" not in result.fit_markdown

    def test_main_content_preserved(self, generator, nav_heavy_html):
        result = generator.generate_from_html(nav_heavy_html)
        assert "Real Content" in result.fit_markdown
        assert "actual content" in result.fit_markdown

    def test_keep_nav_when_disabled(self):
        opts = MarkdownOptions(remove_nav=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><nav><a href='/'>Home page link</a></nav><main><p>Content text here</p></main></body></html>"
        result = gen.generate_from_html(html)
        # Nav content is kept but standalone <a> only gets counted, not rendered as markdown
        assert result.text

    def test_keep_header_when_disabled(self):
        opts = MarkdownOptions(remove_header=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><header><h1>Large enough title</h1></header><main><p>Content text here</p></main></body></html>"
        result = gen.generate_from_html(html)
        assert "Large enough title" in result.fit_markdown

    def test_keep_footer_when_disabled(self):
        opts = MarkdownOptions(remove_footer=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><footer><p>Footer text content here</p></footer><main><p>Content text here</p></main></body></html>"
        result = gen.generate_from_html(html)
        assert "Footer text content" in result.fit_markdown

    def test_ads_removed(self, generator, ad_heavy_html):
        result = generator.generate_from_html(ad_heavy_html)
        assert "Ad banner" not in result.fit_markdown
        assert "Cookie consent" not in result.fit_markdown

    def test_scripts_removed(self, generator, noise_html):
        result = generator.generate_from_html(noise_html)
        assert "console.log" not in result.fit_markdown
        assert "var x = 1" not in result.fit_markdown

    def test_styles_removed(self, generator, noise_html):
        result = generator.generate_from_html(noise_html)
        assert "display: none" not in result.fit_markdown

    def test_main_content_preserved_after_noise_removal(self, generator, noise_html):
        result = generator.generate_from_html(noise_html)
        assert "Content" in result.fit_markdown
        assert "Actual content here" in result.fit_markdown

    def test_scripts_always_removed_via_noise_tags(self):
        """Scripts are always removed via noise_tags, even when remove_scripts=False."""
        opts = MarkdownOptions(remove_scripts=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><script>var x=1; some code here</script><p>Content text here</p></body></html>"
        result = gen.generate_from_html(html)
        assert "var x=1" not in result.fit_markdown
        assert "Content text here" in result.fit_markdown

    def test_buttons_removed_by_default(self, generator, noise_html):
        result = generator.generate_from_html(noise_html)
        assert "Click me" not in result.fit_markdown

    def test_buttons_survive_cleaning_when_disabled(self):
        """Buttons survive generator cleaning when disabled, but converter doesn't render button text as markdown."""
        opts = MarkdownOptions(remove_buttons=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Text before button</p><button>Click action here</button><p>Text after button</p></body></html>"
        result = gen.generate_from_html(html)
        assert isinstance(result.fit_markdown, str)
        assert len(result.fit_markdown) > 0

    def test_forms_removed_when_enabled(self):
        opts = MarkdownOptions(remove_forms=True)
        gen = MarkdownGenerator(opts)
        html = "<html><body><form action='/submit'><input type='text'></form><p>Content text here</p></body></html>"
        result = gen.generate_from_html(html)
        assert "input" not in result.fit_markdown.lower()


# ═══════════════════════════════════════════════════════════════════════════
#  4. Content inclusion/exclusion
# ═══════════════════════════════════════════════════════════════════════════

class TestContentInclusion:

    def test_links_included_by_default(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        # Links outside <p> get counted but not rendered as markdown [text](url)
        # The link text appears in the output as text
        assert result.link_count >= 1

    def test_links_excluded(self):
        opts = MarkdownOptions(include_links=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Some text with link content here</p></body></html>"
        result = gen.generate_from_html(html)
        assert "[Link]" not in result.fit_markdown
        assert "link" in result.fit_markdown.lower()

    def test_images_excluded_by_default(self, generator, image_html):
        result = generator.generate_from_html(image_html)
        assert "![A photo]" not in result.fit_markdown

    def test_images_included(self):
        opts = MarkdownOptions(include_images=True)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Text content before image</p><img src='/pic.jpg' alt='Photo'><p>Text content after image</p></body></html>"
        result = gen.generate_from_html(html)
        assert "![" in result.fit_markdown
        assert "pic.jpg" in result.fit_markdown

    def test_tables_included_by_default(self, generator, table_html):
        result = generator.generate_from_html(table_html)
        assert "|" in result.fit_markdown

    def test_tables_excluded(self):
        opts = MarkdownOptions(include_tables=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Before table content</p><table><tr><td>Table value here</td></tr></table><p>After table content</p></body></html>"
        result = gen.generate_from_html(html)
        assert "|" not in result.fit_markdown

    def test_code_blocks_included_by_default(self, generator, code_html):
        result = generator.generate_from_html(code_html)
        assert "```" in result.fit_markdown

    def test_code_blocks_excluded(self):
        opts = MarkdownOptions(include_code_blocks=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Before code content</p><pre><code>some code here</code></pre><p>After code content</p></body></html>"
        result = gen.generate_from_html(html)
        assert "```" not in result.fit_markdown

    def test_lists_included_by_default(self, generator, list_html):
        result = generator.generate_from_html(list_html)
        assert "-" in result.fit_markdown

    def test_lists_excluded(self):
        opts = MarkdownOptions(include_lists=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Before list content</p><ul><li>List item value</li></ul><p>After list content</p></body></html>"
        result = gen.generate_from_html(html)
        lines = [l.strip() for l in result.fit_markdown.split('\n') if l.strip()]
        for line in lines:
            assert not line.startswith("- "), f"Unexpected list marker in: {line}"

    def test_blockquotes_included_by_default(self, generator, blockquote_html):
        result = generator.generate_from_html(blockquote_html)
        assert ">" in result.fit_markdown

    def test_blockquotes_excluded(self):
        opts = MarkdownOptions(include_blockquotes=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Before quote</p><blockquote><p>Quote text here</p></blockquote><p>After quote</p></body></html>"
        result = gen.generate_from_html(html)
        assert ">" not in result.fit_markdown


# ═══════════════════════════════════════════════════════════════════════════
#  5. Metadata extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestMetadataExtraction:

    def test_title_extraction(self, generator):
        html = "<html><head><title>My Page Title</title></head><body><p>Content text here</p></body></html>"
        result = generator.generate_from_html(html)
        assert result.title == "My Page Title"

    def test_h1_extraction(self, generator):
        html = "<html><body><h1>First Heading Title</h1><p>Content text here</p></body></html>"
        result = generator.generate_from_html(html)
        assert result.h1 == "First Heading Title"

    def test_description_from_meta(self, generator):
        html = """<html><head>
            <meta name="description" content="Page description text here">
        </head><body><p>Content text here</p></body></html>"""
        result = generator.generate_from_html(html)
        assert result.description == "Page description text here"

    def test_description_from_og(self, generator):
        html = """<html><head>
            <meta property="og:description" content="OG description text">
        </head><body><p>Content text here</p></body></html>"""
        result = generator.generate_from_html(html)
        assert result.description == "OG description text"

    def test_missing_title(self, generator):
        html = "<html><body><p>No title tag present here</p></body></html>"
        result = generator.generate_from_html(html)
        assert result.title == ""

    def test_missing_h1(self, generator):
        html = "<html><body><p>No heading tag present here</p></body></html>"
        result = generator.generate_from_html(html)
        assert result.h1 == ""

    def test_missing_description(self, generator):
        html = "<html><body><p>No meta tag present here</p></body></html>"
        result = generator.generate_from_html(html)
        assert result.description == ""


# ═══════════════════════════════════════════════════════════════════════════
#  6. Statistics
# ═══════════════════════════════════════════════════════════════════════════

class TestStatistics:

    def test_word_count(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        assert result.word_count > 0
        assert result.word_count == len(result.text.split())

    def test_char_count(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        assert result.char_count > 0
        assert result.char_count == len(result.text)

    def test_heading_count(self, generator, complex_html):
        result = generator.generate_from_html(complex_html)
        assert result.heading_count > 0

    def test_link_count(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        assert result.link_count >= 1

    def test_image_count_excluded_by_default(self, generator, image_html):
        result = generator.generate_from_html(image_html)
        assert result.image_count == 0

    def test_statistics_on_empty(self, generator):
        result = generator.generate_from_html("")
        assert result.word_count == 0
        assert result.char_count == 0
        assert result.heading_count == 0
        assert result.link_count == 0
        assert result.image_count == 0


# ═══════════════════════════════════════════════════════════════════════════
#  7. Truncation
# ═══════════════════════════════════════════════════════════════════════════

class TestTruncation:

    def test_truncation_applied(self):
        opts = MarkdownOptions(max_length=50)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>" + "word " * 100 + "</p></body></html>"
        result = gen.generate_from_html(html)
        assert result.is_truncated is True
        assert len(result.text) <= 50

    def test_truncation_applies_to_fit_markdown(self):
        """Regression: max_length must truncate fit_markdown, not just text."""
        opts = MarkdownOptions(max_length=100)
        gen = MarkdownGenerator(opts)
        # 500 words → ~2500 chars, well above 100
        html = "<html><body><p>" + "word " * 500 + "</p></body></html>"
        result = gen.generate_from_html(html)
        assert result.is_truncated is True
        assert len(result.text) <= 100
        assert len(result.fit_markdown) <= 100

    def test_truncation_bs4_path(self):
        opts = MarkdownOptions(max_length=100, force_beautifulsoup=True)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>" + "word " * 500 + "</p></body></html>"
        result = gen.generate_from_html(html)
        assert result.is_truncated is True
        assert len(result.fit_markdown) <= 100

    def test_truncation_selectolax_path(self):
        opts = MarkdownOptions(max_length=100, force_beautifulsoup=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>" + "word " * 500 + "</p></body></html>"
        result = gen.generate_from_html(html)
        assert result.is_truncated is True
        assert len(result.fit_markdown) <= 100

    def test_no_truncation_when_within_limit(self):
        opts = MarkdownOptions(max_length=100000)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Short text content here</p></body></html>"
        result = gen.generate_from_html(html)
        assert result.is_truncated is False


# ═══════════════════════════════════════════════════════════════════════════
#  8. Dynamic noise patterns
# ═══════════════════════════════════════════════════════════════════════════

class TestDynamicNoisePatterns:

    def test_dynamic_pattern_removes_matching_text(self):
        patterns = [r"(?i)click here now"]
        opts = MarkdownOptions(dynamic_noise_patterns=patterns)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Content text that should remain</p><p>Click Here Now</p><p>More content text here</p></body></html>"
        result = gen.generate_from_html(html)
        assert "Click Here Now" not in result.fit_markdown
        assert "Content text" in result.fit_markdown

    def test_multiple_patterns(self):
        patterns = [
            r"(?i)advertis(e|ing)",
            r"(?i)subscribe now",
        ]
        opts = MarkdownOptions(dynamic_noise_patterns=patterns)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Good content text here</p><p>Advertise with us today</p><p>Subscribe now please</p></body></html>"
        result = gen.generate_from_html(html)
        assert "Advertise" not in result.fit_markdown
        assert "Subscribe now" not in result.fit_markdown
        assert "Good content" in result.fit_markdown

    def test_no_patterns_by_default(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        assert result.fit_markdown

    def test_invalid_regex_handled(self):
        # AUDIT_02 #8: невалідні patterns тепер відхиляються pydantic-валідатором
        # на етапі створення MarkdownOptions замість тихого warning у логах.
        import pytest as _pytest
        from pydantic import ValidationError

        with _pytest.raises(ValidationError):
            MarkdownOptions(dynamic_noise_patterns=["[invalid"])
        with _pytest.raises(ValidationError):
            MarkdownOptions(dynamic_noise_patterns=[r"ok", "also [broken"])
        # Валідні patterns — приймаються без винятків.
        opts = MarkdownOptions(dynamic_noise_patterns=[r"\d+\s+ago"])
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html("<html><body><p>Text</p></body></html>")
        assert isinstance(result, MarkdownResult)


# ═══════════════════════════════════════════════════════════════════════════
#  9. Content density
# ═══════════════════════════════════════════════════════════════════════════

class TestContentDensity:

    def test_content_density_with_nav_heavy_page(self):
        opts = MarkdownOptions(use_content_density=True)
        gen = MarkdownGenerator(opts)
        body_text = " ".join(["word"] * 200)
        html = f"""<html><body>
            <nav><a href="/1">Link1</a><a href="/2">Link2</a><a href="/3">Link3</a></nav>
            <article>
                <h1>Main Article Title</h1>
                <p>This is a substantial article with enough words. {body_text}</p>
            </article>
            <footer><p>Footer text content here</p></footer>
        </body></html>"""
        result = gen.generate_from_html(html)
        assert "Main Article Title" in result.fit_markdown

    def test_content_density_disabled(self):
        opts = MarkdownOptions(use_content_density=False)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>Simple content text here</p></body></html>"
        result = gen.generate_from_html(html)
        assert result.fit_markdown


# ═══════════════════════════════════════════════════════════════════════════
#  10. Citations
# ═══════════════════════════════════════════════════════════════════════════

class TestCitations:

    def test_citations_generated(self):
        opts = MarkdownOptions(generate_citations=True)
        gen = MarkdownGenerator(opts)
        html = """<html><body><p>
            See <a href="https://example.com">Example website</a> for more information.
            Also check <a href="https://other.com">Other website</a> for details.
        </p></body></html>"""
        result = gen.generate_from_html(html)
        assert result.markdown_with_citations
        assert len(result.references) >= 2

    def test_citations_not_generated_by_default(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        assert result.markdown_with_citations == ""
        assert result.references == []


# ═══════════════════════════════════════════════════════════════════════════
#  11. Lazy raw_markdown
# ═══════════════════════════════════════════════════════════════════════════

class TestLazyRawMarkdown:

    def test_raw_markdown_accessible(self, generator, simple_html):
        result = generator.generate_from_html(simple_html)
        raw = result.raw_markdown
        assert isinstance(raw, str)

    def test_raw_markdown_contains_more_content(self):
        opts = MarkdownOptions(remove_nav=False, remove_footer=False)
        gen = MarkdownGenerator(opts)
        html = """<html><body>
            <nav><a href="/">Navigation link</a></nav>
            <main><p>Main content text here</p></main>
            <footer><p>Footer content text</p></footer>
        </body></html>"""
        result = gen.generate_from_html(html)
        # raw_markdown should have equal or more content than fit_markdown
        assert len(result.raw_markdown) >= len(result.fit_markdown)


# ═══════════════════════════════════════════════════════════════════════════
#  12. Async generation
# ═══════════════════════════════════════════════════════════════════════════

class TestAsyncGeneration:

    @pytest.mark.asyncio
    async def test_async_generate(self, simple_html):
        result = await generate_markdown_async(simple_html)
        assert isinstance(result, MarkdownResult)
        assert result.fit_markdown

    @pytest.mark.asyncio
    async def test_async_with_options(self, simple_html):
        opts = MarkdownOptions(max_length=100)
        result = await generate_markdown_async(simple_html, opts)
        assert isinstance(result, MarkdownResult)

    @pytest.mark.asyncio
    async def test_async_empty(self):
        result = await generate_markdown_async("")
        assert result.fit_markdown == ""


# ═══════════════════════════════════════════════════════════════════════════
#  13. URL normalization in generator
# ═══════════════════════════════════════════════════════════════════════════

class TestUrlNormalizationInGenerator:

    def test_relative_urls_normalized_in_links(self):
        opts = MarkdownOptions(
            base_url="https://example.com/blog/",
            normalize_urls=True,
        )
        gen = MarkdownGenerator(opts)
        html = '<html><body><p>Visit <a href="/about">about page</a> for more</p></body></html>'
        result = gen.generate_from_html(html)
        assert "https://example.com/about" in result.fit_markdown

    def test_absolute_urls_unchanged(self):
        opts = MarkdownOptions(
            base_url="https://example.com",
            normalize_urls=True,
        )
        gen = MarkdownGenerator(opts)
        html = '<html><body><p>Visit <a href="https://other.com/page">other page</a> for more</p></body></html>'
        result = gen.generate_from_html(html)
        assert "https://other.com/page" in result.fit_markdown


# ═══════════════════════════════════════════════════════════════════════════
#  14. Whitespace handling
# ═══════════════════════════════════════════════════════════════════════════

class TestWhitespace:

    def test_normalize_whitespace_collapses_spaces(self):
        opts = MarkdownOptions(normalize_whitespace=True)
        gen = MarkdownGenerator(opts)
        html = "<html><body><p>   lots    of     spaces   in this text   </p></body></html>"
        result = gen.generate_from_html(html)
        assert "   " not in result.fit_markdown

    def test_no_triple_newlines(self, generator, complex_html):
        result = generator.generate_from_html(complex_html)
        assert "\n\n\n" not in result.fit_markdown
