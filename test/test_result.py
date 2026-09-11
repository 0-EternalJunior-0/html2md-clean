"""Comprehensive tests for MarkdownResult.

Tests:
- Default values
- model_post_init stats calculation
- Lazy raw_markdown
- markdown property alias
- to_dict()
- empty() class method
- __bool__
- __repr__
"""

import pytest

from markdown.result import MarkdownResult
from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions


# ═══════════════════════════════════════════════════════════════════════════
#  1. Default values
# ═══════════════════════════════════════════════════════════════════════════

class TestDefaults:

    def test_empty_result_defaults(self):
        r = MarkdownResult()
        assert r.text == ""
        assert r.fit_markdown == ""
        assert r.markdown_with_citations == ""
        assert r.references == []
        assert r.title == ""
        assert r.h1 == ""
        assert r.description == ""
        assert r.word_count == 0
        assert r.char_count == 0
        assert r.heading_count == 0
        assert r.link_count == 0
        assert r.image_count == 0
        assert r.is_truncated is False

    def test_result_with_content(self):
        r = MarkdownResult(
            text="Hello world",
            fit_markdown="# Hello world",
        )
        assert r.text == "Hello world"
        assert r.fit_markdown == "# Hello world"


# ═══════════════════════════════════════════════════════════════════════════
#  2. model_post_init stats
# ═══════════════════════════════════════════════════════════════════════════

class TestStatsCalculation:

    def test_word_count_calculated(self):
        r = MarkdownResult(text="one two three four")
        assert r.word_count == 4

    def test_char_count_calculated(self):
        r = MarkdownResult(text="hello")
        assert r.char_count == 5

    def test_word_count_not_overwritten(self):
        """If word_count is explicitly set, model_post_init should not overwrite."""
        r = MarkdownResult(text="one two", word_count=999)
        assert r.word_count == 999

    def test_empty_text_zero_stats(self):
        r = MarkdownResult(text="")
        assert r.word_count == 0
        assert r.char_count == 0


# ═══════════════════════════════════════════════════════════════════════════
#  3. markdown property alias
# ═══════════════════════════════════════════════════════════════════════════

class TestMarkdownAlias:

    def test_markdown_is_fit_markdown(self):
        r = MarkdownResult(fit_markdown="# Hello")
        assert r.markdown == "# Hello"
        assert r.markdown == r.fit_markdown

    def test_markdown_changes_with_fit_markdown(self):
        r = MarkdownResult(fit_markdown="original")
        r.fit_markdown = "updated"
        assert r.markdown == "updated"


# ═══════════════════════════════════════════════════════════════════════════
#  4. Lazy raw_markdown
# ═══════════════════════════════════════════════════════════════════════════

class TestLazyRawMarkdown:

    def test_raw_markdown_not_generated_when_not_set(self):
        r = MarkdownResult()
        assert r.raw_markdown == ""

    def test_raw_markdown_manual_set(self):
        r = MarkdownResult()
        r.raw_markdown = "manual value"
        assert r.raw_markdown == "manual value"

    def test_raw_markdown_via_setter(self):
        r = MarkdownResult()
        r.raw_markdown = "# Custom"
        assert r.raw_markdown == "# Custom"

    def test_set_lazy_raw_markdown(self):
        gen = MarkdownGenerator()
        r = MarkdownResult()
        r.set_lazy_raw_markdown("<html><body><p>Test</p></body></html>", gen)
        raw = r.raw_markdown
        assert isinstance(raw, str)

    def test_to_dict_includes_raw_markdown(self):
        r = MarkdownResult()
        r.raw_markdown = "raw content"
        d = r.to_dict()
        assert d["raw_markdown"] == "raw content"


# ═══════════════════════════════════════════════════════════════════════════
#  5. to_dict()
# ═══════════════════════════════════════════════════════════════════════════

class TestToDict:

    def test_to_dict_returns_dict(self):
        r = MarkdownResult(text="hello", fit_markdown="# hello")
        d = r.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_contains_all_fields(self):
        r = MarkdownResult(
            text="hello",
            fit_markdown="# hello",
            title="Title",
            h1="H1",
            description="Desc",
            word_count=1,
            char_count=5,
            heading_count=1,
            link_count=0,
            image_count=0,
            is_truncated=False,
        )
        d = r.to_dict()
        assert d["text"] == "hello"
        assert d["fit_markdown"] == "# hello"
        assert d["title"] == "Title"
        assert d["h1"] == "H1"
        assert d["description"] == "Desc"
        assert d["word_count"] == 1
        assert "raw_markdown" in d  # key should be included


# ═══════════════════════════════════════════════════════════════════════════
#  6. empty()
# ═══════════════════════════════════════════════════════════════════════════

class TestEmpty:

    def test_empty_returns_result(self):
        r = MarkdownResult.empty()
        assert isinstance(r, MarkdownResult)

    def test_empty_has_no_content(self):
        r = MarkdownResult.empty()
        assert r.text == ""
        assert r.fit_markdown == ""
        assert r.word_count == 0
        assert bool(r) is False


# ═══════════════════════════════════════════════════════════════════════════
#  7. __bool__
# ═══════════════════════════════════════════════════════════════════════════

class TestBool:

    def test_empty_result_falsy(self):
        assert bool(MarkdownResult()) is False

    def test_result_with_text_truthy(self):
        assert bool(MarkdownResult(text="content")) is True

    def test_result_with_fit_markdown_truthy(self):
        assert bool(MarkdownResult(fit_markdown="# Title")) is True

    def test_result_with_only_metadata_falsy(self):
        """Only metadata fields should not make it truthy."""
        r = MarkdownResult(title="Title", h1="H1")
        assert bool(r) is False


# ═══════════════════════════════════════════════════════════════════════════
#  8. __repr__
# ═══════════════════════════════════════════════════════════════════════════

class TestRepr:

    def test_repr_contains_stats(self):
        r = MarkdownResult(text="hello world foo", fit_markdown="# hello")
        repr_str = repr(r)
        assert "words=" in repr_str
        assert "chars=" in repr_str
        assert "truncated=" in repr_str

    def test_repr_empty(self):
        r = MarkdownResult()
        repr_str = repr(r)
        assert "words=0" in repr_str
        assert "chars=0" in repr_str


# ═══════════════════════════════════════════════════════════════════════════
#  9. Model validation
# ═══════════════════════════════════════════════════════════════════════════

class TestModelValidation:

    def test_validate_assignment(self):
        r = MarkdownResult()
        r.text = "new text"
        assert r.text == "new text"

    def test_not_frozen(self):
        r = MarkdownResult()
        r.fit_markdown = "modified"
        assert r.fit_markdown == "modified"

    def test_ge_constraints(self):
        """Fields with ge=0 should reject negative values."""
        r = MarkdownResult()
        with pytest.raises(Exception):
            r.word_count = -1
        with pytest.raises(Exception):
            r.char_count = -1
        with pytest.raises(Exception):
            r.heading_count = -1
        with pytest.raises(Exception):
            r.link_count = -1
        with pytest.raises(Exception):
            r.image_count = -1
