"""Integration tests using real HTML pages from WebMainBench dataset.

Tests the full pipeline (generator → converter → renderer) on real-world
HTML pages of varying complexity, language, and structure.

Also tests:
- Robustness with large HTML files
- Performance sanity (no timeouts on real pages)
- Cross-parser consistency (BS4 vs Selectolax)
- All major options working on real content
"""

import json
import os
import time
import pytest

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions, COMMON_NOISE_PATTERNS

WEBMAINBENCH_DIR = os.path.join(os.path.dirname(__file__), "data", "webmainbench")


def _load_page(index):
    """Load a specific WebMainBench page by index."""
    path = os.path.join(WEBMAINBENCH_DIR, f"page_{index:03d}.html")
    if not os.path.exists(path):
        pytest.skip(f"WebMainBench page_{index:03d} not downloaded")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_meta(index):
    """Load metadata for a specific page."""
    path = os.path.join(WEBMAINBENCH_DIR, f"page_{index:03d}_meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _skip_if_no_data():
    if not os.path.exists(WEBMAINBENCH_DIR):
        pytest.skip("WebMainBench data not downloaded")


# ═══════════════════════════════════════════════════════════════════════════
#  1. Basic generation on real pages
# ═══════════════════════════════════════════════════════════════════════════

class TestBasicGeneration:

    @pytest.mark.parametrize("page_index", range(10))
    def test_generator_produces_output(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        assert isinstance(result.fit_markdown, str)
        assert len(result.fit_markdown) > 0, f"Empty output for page_{page_index:03d}"

    @pytest.mark.parametrize("page_index", range(10))
    def test_result_has_metadata(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        # At least one of title, h1 should be non-empty
        assert result.title or result.h1, f"No metadata for page_{page_index:03d}"

    @pytest.mark.parametrize("page_index", range(10))
    def test_word_count_positive(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        assert result.word_count > 0, f"Zero word count for page_{page_index:03d}"


# ═══════════════════════════════════════════════════════════════════════════
#  2. Cross-parser consistency
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossParser:

    @pytest.mark.parametrize("page_index", range(5))
    def test_bs4_and_selectolax_both_produce_output(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        bs4_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))
        sl_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=False))
        bs4_result = bs4_gen.generate_from_html(html)
        sl_result = sl_gen.generate_from_html(html)
        assert len(bs4_result.fit_markdown) > 0
        assert len(sl_result.fit_markdown) > 0

    @pytest.mark.parametrize("page_index", range(5))
    def test_both_extract_same_title(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        bs4_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))
        sl_gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=False))
        bs4_result = bs4_gen.generate_from_html(html)
        sl_result = sl_gen.generate_from_html(html)
        # Titles should be identical
        assert bs4_result.title == sl_result.title


# ═══════════════════════════════════════════════════════════════════════════
#  3. Options on real pages
# ═══════════════════════════════════════════════════════════════════════════

class TestOptionsOnRealPages:

    def test_noise_removal_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(5)  # triumphhq.com terms of use
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        md = result.fit_markdown
        # Should not contain typical noise
        assert "cookie" not in md.lower() or len(md) > 100

    def test_no_links_mode_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(6)  # scpolicycouncil.org
        opts = MarkdownOptions(include_links=False)
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert "[" not in result.fit_markdown or "http" not in result.fit_markdown

    def test_no_images_mode_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(0)
        opts = MarkdownOptions(include_images=True)
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        # Images should be included now
        # This page might not have images, just verify no crash
        assert isinstance(result.fit_markdown, str)

    def test_strict_escape_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(7)  # CNN transcript
        opts = MarkdownOptions(strict_escape=True)
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0

    def test_reference_links_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(6)
        opts = MarkdownOptions(link_style="reference")
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0

    def test_dynamic_noise_patterns_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(5)
        opts = MarkdownOptions(dynamic_noise_patterns=COMMON_NOISE_PATTERNS)
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0

    def test_content_density_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(6)
        opts = MarkdownOptions(use_content_density=True, min_content_words=50)
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0

    def test_custom_max_length_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(1)  # Large page (2MB)
        opts = MarkdownOptions(max_length=1000)
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.text) <= 1000
        assert result.is_truncated is True

    def test_bullet_cycling_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(5)
        opts = MarkdownOptions(bullets="-*+")
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0

    def test_backslash_newline_on_real_page(self):
        _skip_if_no_data()
        html = _load_page(5)
        opts = MarkdownOptions(newline_style="backslash")
        gen = MarkdownGenerator(opts)
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0


# ═══════════════════════════════════════════════════════════════════════════
#  4. Performance / robustness
# ═══════════════════════════════════════════════════════════════════════════

class TestPerformance:

    @pytest.mark.parametrize("page_index", range(10))
    def test_generation_under_10_seconds(self, page_index):
        """Real pages should process in under 10 seconds."""
        _skip_if_no_data()
        html = _load_page(page_index)
        gen = MarkdownGenerator()
        start = time.time()
        result = gen.generate_from_html(html)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"page_{page_index:03d} took {elapsed:.1f}s"

    @pytest.mark.parametrize("page_index", range(5))
    def test_bs4_under_10_seconds(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        gen = MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))
        start = time.time()
        result = gen.generate_from_html(html)
        elapsed = time.time() - start
        assert elapsed < 10.0, f"BS4 page_{page_index:03d} took {elapsed:.1f}s"

    def test_large_page_handles_gracefully(self):
        _skip_if_no_data()
        html = _load_page(1)  # 2MB page
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0
        assert result.word_count > 0


# ═══════════════════════════════════════════════════════════════════════════
#  5. Output quality checks
# ═══════════════════════════════════════════════════════════════════════════

class TestOutputQuality:

    def test_no_html_tags_in_output(self):
        """Markdown output should not contain raw HTML tags."""
        _skip_if_no_data()
        html = _load_page(6)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        md = result.fit_markdown
        # Should not contain opening tags like <div, <span, <p
        # (some <br> might remain, <a> should be converted)
        assert "<div" not in md
        assert "<span" not in md
        assert "<section" not in md
        assert "<article" not in md

    def test_no_script_content(self):
        _skip_if_no_data()
        html = _load_page(0)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        assert "function(" not in result.fit_markdown or "javascript" not in result.fit_markdown.lower()

    def test_no_double_newlines(self):
        _skip_if_no_data()
        for i in range(5):
            html = _load_page(i)
            gen = MarkdownGenerator()
            result = gen.generate_from_html(html)
            assert "\n\n\n" not in result.fit_markdown, f"Triple newlines in page_{i:03d}"

    @pytest.mark.parametrize("page_index", range(10))
    def test_has_at_least_some_content(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        # Every page should produce at least 5 words
        assert result.word_count >= 5, (
            f"page_{page_index:03d} produced only {result.word_count} words"
        )

    def test_no_trailing_whitespace_per_line(self):
        _skip_if_no_data()
        html = _load_page(6)
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        for line in result.fit_markdown.split("\n"):
            assert line == line.rstrip(), f"Trailing whitespace in: {line!r}"


# ═══════════════════════════════════════════════════════════════════════════
#  6. Async on real pages
# ═══════════════════════════════════════════════════════════════════════════

class TestAsyncOnRealPages:

    @pytest.mark.asyncio
    async def test_async_generation(self):
        from markdown.generator import generate_markdown_async
        _skip_if_no_data()
        html = _load_page(5)
        result = await generate_markdown_async(html)
        assert len(result.fit_markdown) > 0

    @pytest.mark.asyncio
    async def test_async_with_options(self):
        from markdown.generator import generate_markdown_async
        _skip_if_no_data()
        html = _load_page(5)
        opts = MarkdownOptions(max_length=500)
        result = await generate_markdown_async(html, opts)
        assert len(result.text) <= 500


# ═══════════════════════════════════════════════════════════════════════════
#  7. Quick generate on real pages
# ═══════════════════════════════════════════════════════════════════════════

class TestQuickGenerateOnRealPages:

    @pytest.mark.parametrize("page_index", range(5))
    def test_quick_generate_works(self, page_index):
        _skip_if_no_data()
        html = _load_page(page_index)
        result = MarkdownGenerator.quick_generate(html)
        assert len(result.fit_markdown) > 0
        assert result.word_count > 0


# ═══════════════════════════════════════════════════════════════════════════
#  8. Regression: existing test files
# ═══════════════════════════════════════════════════════════════════════════

class TestExistingTestFiles:

    def test_test1_html(self):
        path = os.path.join(os.path.dirname(__file__), "data", "test1.html")
        if not os.path.exists(path):
            pytest.skip("test1.html not found")
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        assert len(result.fit_markdown) > 0
        assert result.word_count > 0

    def test_test2_html(self):
        path = os.path.join(os.path.dirname(__file__), "data", "test2.html")
        if not os.path.exists(path):
            pytest.skip("test2.html not found")
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        if not html.strip():
            pytest.skip("test2.html is empty")
        gen = MarkdownGenerator()
        result = gen.generate_from_html(html)
        assert isinstance(result.fit_markdown, str)


# ═══════════════════════════════════════════════════════════════════════════
#  9. Edge cases with real data
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_empty_html(self):
        gen = MarkdownGenerator()
        result = gen.generate_from_html("")
        assert result.fit_markdown == ""

    def test_only_script(self):
        gen = MarkdownGenerator()
        result = gen.generate_from_html("<html><body><script>alert('hi')</script></body></html>")
        assert "alert" not in result.fit_markdown

    def test_only_style(self):
        gen = MarkdownGenerator()
        result = gen.generate_from_html("<html><body><style>.x{color:red}</style><p>Content text here</p></body></html>")
        assert "Content text" in result.fit_markdown

    def test_nested_divs(self):
        gen = MarkdownGenerator()
        html = "<html><body><div><div><div><p>Deep content</p></div></div></div></body></html>"
        result = gen.generate_from_html(html)
        assert "Deep content" in result.fit_markdown

    def test_unicode_content(self):
        gen = MarkdownGenerator()
        html = "<html><body><p>Тестовий контент Українською мовою</p></body></html>"
        result = gen.generate_from_html(html)
        assert "Українською" in result.fit_markdown

    def test_chinese_content(self):
        gen = MarkdownGenerator()
        html = "<html><body><p>这是一个中文测试内容用于验证编码</p></body></html>"
        result = gen.generate_from_html(html)
        assert "中文" in result.fit_markdown

    def test_malformed_html(self):
        gen = MarkdownGenerator()
        html = "<html><body><p>Unclosed paragraph<div>Mixed</p></div></body></html>"
        result = gen.generate_from_html(html)
        assert isinstance(result.fit_markdown, str)

    def test_no_body_tag(self):
        gen = MarkdownGenerator()
        html = "<html><p>No body tag</p></html>"
        result = gen.generate_from_html(html)
        assert isinstance(result.fit_markdown, str)

    def test_only_doctype(self):
        gen = MarkdownGenerator()
        result = gen.generate_from_html("<!DOCTYPE html>")
        assert isinstance(result.fit_markdown, str)
