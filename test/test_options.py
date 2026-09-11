"""Comprehensive tests for MarkdownOptions.

Tests every configurable parameter in the MarkdownOptions model:
- Noise removal flags (remove_nav, remove_header, remove_footer, etc.)
- Content inclusion flags (include_links, include_images, etc.)
- Constraints (max_length, min_paragraph_length, min_heading_length)
- Formatting options (preserve_whitespace, normalize_whitespace, etc.)
- URL options (base_url, normalize_urls)
- Content density (use_content_density, link_density_threshold, min_content_words)
- Parser selection (force_beautifulsoup)
- Dynamic noise patterns
- Bullet cycling and newline style
- Strict escaping and link style
- Methods: should_remove_tag, should_remove_by_class, should_remove_by_id, with_overrides
"""

import pytest
from markdown.options import MarkdownOptions, COMMON_NOISE_PATTERNS


# ═══════════════════════════════════════════════════════════════════════════
#  1. Default values
# ═══════════════════════════════════════════════════════════════════════════

class TestDefaults:
    """Verify every default value matches the documented spec."""

    def test_noise_removal_defaults(self):
        opts = MarkdownOptions()
        assert opts.remove_nav is True
        assert opts.remove_header is True
        assert opts.remove_footer is True
        assert opts.remove_aside is True
        assert opts.remove_ads is True
        assert opts.remove_scripts is True
        assert opts.remove_buttons is True
        assert opts.remove_forms is False

    def test_include_defaults(self):
        opts = MarkdownOptions()
        assert opts.include_links is True
        assert opts.include_images is False
        assert opts.include_tables is True
        assert opts.include_code_blocks is True
        assert opts.include_lists is True
        assert opts.include_blockquotes is True

    def test_constraint_defaults(self):
        opts = MarkdownOptions()
        assert opts.max_length == 100000
        assert opts.min_paragraph_length == 3
        assert opts.min_heading_length == 1

    def test_whitespace_defaults(self):
        opts = MarkdownOptions()
        assert opts.preserve_whitespace is False
        assert opts.normalize_whitespace is True

    def test_citation_default(self):
        opts = MarkdownOptions()
        assert opts.generate_citations is False

    def test_url_defaults(self):
        opts = MarkdownOptions()
        assert opts.base_url == ""
        assert opts.normalize_urls is True

    def test_content_density_defaults(self):
        opts = MarkdownOptions()
        assert opts.use_content_density is False
        assert opts.link_density_threshold == 0.5
        assert opts.min_content_words == 100

    def test_parser_default(self):
        opts = MarkdownOptions()
        assert opts.force_beautifulsoup is False

    def test_dynamic_noise_default(self):
        opts = MarkdownOptions()
        assert opts.dynamic_noise_patterns == []

    def test_extract_div_text_default(self):
        opts = MarkdownOptions()
        assert opts.extract_div_text is True

    def test_preserve_inline_formatting_default(self):
        opts = MarkdownOptions()
        assert opts.preserve_inline_formatting is True

    def test_bullets_default(self):
        opts = MarkdownOptions()
        assert opts.bullets == "-"

    def test_newline_style_default(self):
        opts = MarkdownOptions()
        assert opts.newline_style == "spaces"

    def test_strict_escape_default(self):
        opts = MarkdownOptions()
        assert opts.strict_escape is False

    def test_link_style_default(self):
        opts = MarkdownOptions()
        assert opts.link_style == "inline"

    def test_noise_tags_default(self):
        opts = MarkdownOptions()
        expected = {
            "script", "style", "noscript", "template", "svg", "canvas",
            "iframe", "embed", "object", "video", "audio",
            "select", "option", "optgroup",
        }
        assert opts.noise_tags == frozenset(expected)

    def test_noise_classes_default(self):
        opts = MarkdownOptions()
        expected = {
            "ad", "ads", "advertisement", "advert", "banner", "sidebar",
            "cookie", "popup", "modal", "overlay", "newsletter",
            "subscribe", "social", "share", "comment", "comments",
            "related", "recommended",
        }
        assert opts.noise_classes == frozenset(expected)

    def test_noise_ids_default(self):
        opts = MarkdownOptions()
        expected = {
            "cookie", "popup", "modal", "overlay", "ad", "ads",
            "sidebar", "newsletter", "comments",
        }
        assert opts.noise_ids == frozenset(expected)


# ═══════════════════════════════════════════════════════════════════════════
#  2. Custom values / override
# ═══════════════════════════════════════════════════════════════════════════

class TestCustomValues:
    """Construct MarkdownOptions with non-default values."""

    def test_all_flags_off(self):
        opts = MarkdownOptions(
            remove_nav=False,
            remove_header=False,
            remove_footer=False,
            remove_aside=False,
            remove_ads=False,
            remove_scripts=False,
            remove_buttons=False,
            remove_forms=True,
            include_links=False,
            include_images=True,
            include_tables=False,
            include_code_blocks=False,
            include_lists=False,
            include_blockquotes=False,
        )
        assert opts.remove_nav is False
        assert opts.remove_header is False
        assert opts.remove_footer is False
        assert opts.remove_aside is False
        assert opts.remove_ads is False
        assert opts.remove_scripts is False
        assert opts.remove_buttons is False
        assert opts.remove_forms is True
        assert opts.include_links is False
        assert opts.include_images is True
        assert opts.include_tables is False
        assert opts.include_code_blocks is False
        assert opts.include_lists is False
        assert opts.include_blockquotes is False

    def test_custom_constraints(self):
        opts = MarkdownOptions(
            max_length=5000,
            min_paragraph_length=5,
            min_heading_length=1,
        )
        assert opts.max_length == 5000
        assert opts.min_paragraph_length == 5
        assert opts.min_heading_length == 1

    def test_custom_url_options(self):
        opts = MarkdownOptions(
            base_url="https://example.com",
            normalize_urls=True,
        )
        assert opts.base_url == "https://example.com"
        assert opts.normalize_urls is True

    def test_custom_content_density(self):
        opts = MarkdownOptions(
            use_content_density=True,
            link_density_threshold=0.3,
            min_content_words=200,
        )
        assert opts.use_content_density is True
        assert opts.link_density_threshold == 0.3
        assert opts.min_content_words == 200

    def test_custom_noise_tags(self):
        opts = MarkdownOptions(noise_tags=frozenset({"custom_tag", "another"}))
        assert "custom_tag" in opts.noise_tags
        assert "another" in opts.noise_tags
        # Default tags should not be present
        assert "script" not in opts.noise_tags

    def test_custom_noise_classes(self):
        opts = MarkdownOptions(noise_classes=frozenset({"my-ad", "tracking"}))
        assert "my-ad" in opts.noise_classes
        assert "tracking" in opts.noise_classes

    def test_custom_noise_ids(self):
        opts = MarkdownOptions(noise_ids=frozenset({"my-popup"}))
        assert "my-popup" in opts.noise_ids

    def test_dynamic_noise_patterns(self):
        patterns = [r"(?i)click here", r"\d+\s+views"]
        opts = MarkdownOptions(dynamic_noise_patterns=patterns)
        assert opts.dynamic_noise_patterns == patterns

    def test_bullets_custom(self):
        opts = MarkdownOptions(bullets="*+>")
        assert opts.bullets == "*+>"

    def test_newline_style_backslash(self):
        opts = MarkdownOptions(newline_style="backslash")
        assert opts.newline_style == "backslash"

    def test_strict_escape_on(self):
        opts = MarkdownOptions(strict_escape=True)
        assert opts.strict_escape is True

    def test_link_style_reference(self):
        opts = MarkdownOptions(link_style="reference")
        assert opts.link_style == "reference"


# ═══════════════════════════════════════════════════════════════════════════
#  3. Validation (pydantic constraints)
# ═══════════════════════════════════════════════════════════════════════════

class TestValidation:
    """Pydantic field constraints should reject invalid values."""

    def test_max_length_must_be_non_negative(self):
        with pytest.raises(Exception):
            MarkdownOptions(max_length=-1)

    def test_min_paragraph_length_must_be_non_negative(self):
        with pytest.raises(Exception):
            MarkdownOptions(min_paragraph_length=-1)

    def test_min_heading_length_must_be_non_negative(self):
        with pytest.raises(Exception):
            MarkdownOptions(min_heading_length=-1)

    def test_link_density_threshold_must_be_in_range(self):
        with pytest.raises(Exception):
            MarkdownOptions(link_density_threshold=1.5)
        with pytest.raises(Exception):
            MarkdownOptions(link_density_threshold=-0.1)

    def test_link_density_threshold_valid_range(self):
        opts = MarkdownOptions(link_density_threshold=0.0)
        assert opts.link_density_threshold == 0.0
        opts = MarkdownOptions(link_density_threshold=1.0)
        assert opts.link_density_threshold == 1.0

    def test_min_content_words_non_negative(self):
        with pytest.raises(Exception):
            MarkdownOptions(min_content_words=-1)

    def test_max_length_zero(self):
        opts = MarkdownOptions(max_length=0)
        assert opts.max_length == 0


# ═══════════════════════════════════════════════════════════════════════════
#  4. should_remove_tag()
# ═══════════════════════════════════════════════════════════════════════════

class TestShouldRemoveTag:
    """Test should_remove_tag() method for every structural tag."""

    def test_noise_tags_always_removed(self):
        opts = MarkdownOptions()
        for tag in ["script", "style", "noscript", "template", "svg",
                    "canvas", "iframe", "embed", "object", "video", "audio",
                    "select", "option", "optgroup"]:
            assert opts.should_remove_tag(tag) is True, f"{tag} should be removed"

    def test_noise_tag_case_insensitive(self):
        opts = MarkdownOptions()
        assert opts.should_remove_tag("SCRIPT") is True
        assert opts.should_remove_tag("Script") is True
        assert opts.should_remove_tag("STYLE") is True

    def test_nav_removal(self):
        opts = MarkdownOptions(remove_nav=True)
        assert opts.should_remove_tag("nav") is True
        opts = MarkdownOptions(remove_nav=False)
        assert opts.should_remove_tag("nav") is False

    def test_header_removal(self):
        opts = MarkdownOptions(remove_header=True)
        assert opts.should_remove_tag("header") is True
        opts = MarkdownOptions(remove_header=False)
        assert opts.should_remove_tag("header") is False

    def test_footer_removal(self):
        opts = MarkdownOptions(remove_footer=True)
        assert opts.should_remove_tag("footer") is True
        opts = MarkdownOptions(remove_footer=False)
        assert opts.should_remove_tag("footer") is False

    def test_aside_removal(self):
        opts = MarkdownOptions(remove_aside=True)
        assert opts.should_remove_tag("aside") is True
        opts = MarkdownOptions(remove_aside=False)
        assert opts.should_remove_tag("aside") is False

    def test_button_removal(self):
        opts = MarkdownOptions(remove_buttons=True)
        assert opts.should_remove_tag("button") is True
        opts = MarkdownOptions(remove_buttons=False)
        assert opts.should_remove_tag("button") is False

    def test_form_removal(self):
        opts = MarkdownOptions(remove_forms=True)
        assert opts.should_remove_tag("form") is True
        opts = MarkdownOptions(remove_forms=False)
        assert opts.should_remove_tag("form") is False

    def test_content_tags_not_removed(self):
        opts = MarkdownOptions()
        for tag in ["p", "div", "span", "a", "h1", "h2", "ul", "ol",
                    "table", "img", "pre", "blockquote", "hr", "dl"]:
            assert opts.should_remove_tag(tag) is False, f"{tag} should NOT be removed"

    def test_unknown_tag_not_removed(self):
        opts = MarkdownOptions()
        assert opts.should_remove_tag("custom-element") is False
        assert opts.should_remove_tag("my-widget") is False

    def test_all_structural_removals_off(self):
        opts = MarkdownOptions(
            remove_nav=False, remove_header=False, remove_footer=False,
            remove_aside=False, remove_buttons=False, remove_forms=False,
        )
        assert opts.should_remove_tag("nav") is False
        assert opts.should_remove_tag("header") is False
        assert opts.should_remove_tag("footer") is False
        assert opts.should_remove_tag("aside") is False
        assert opts.should_remove_tag("button") is False
        assert opts.should_remove_tag("form") is False
        # Noise tags still removed
        assert opts.should_remove_tag("script") is True


# ═══════════════════════════════════════════════════════════════════════════
#  5. should_remove_by_class()
# ═══════════════════════════════════════════════════════════════════════════

class TestShouldRemoveByClass:

    def test_exact_noise_class_match(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_class("ad") is True
        assert opts.should_remove_by_class("ads") is True
        assert opts.should_remove_by_class("popup") is True
        assert opts.should_remove_by_class("cookie") is True
        assert opts.should_remove_by_class("modal") is True
        assert opts.should_remove_by_class("newsletter") is True
        assert opts.should_remove_by_class("social") is True
        assert opts.should_remove_by_class("share") is True
        assert opts.should_remove_by_class("comment") is True
        assert opts.should_remove_by_class("related") is True
        assert opts.should_remove_by_class("recommended") is True

    def test_multi_class_match(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_class("container ad sidebar") is True
        assert opts.should_remove_by_class("wrapper popup overlay") is True

    def test_no_match(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_class("content") is False
        assert opts.should_remove_by_class("main-text") is False
        assert opts.should_remove_by_class("article-body") is False

    def test_empty_class(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_class("") is False

    def test_none_class(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_class(None) is False

    def test_remove_ads_disabled(self):
        opts = MarkdownOptions(remove_ads=False)
        assert opts.should_remove_by_class("ad") is False
        assert opts.should_remove_by_class("popup") is False

    def test_case_insensitive(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_class("AD") is True
        assert opts.should_remove_by_class("Popup") is True
        assert opts.should_remove_by_class("COOKIE") is True

    def test_partial_match_not_triggered(self):
        """Noise classes should match as whole words, not substrings."""
        opts = MarkdownOptions(remove_ads=True)
        # 'adds' contains 'ads' but they are different whole classes
        assert opts.should_remove_by_class("adds") is False


# ═══════════════════════════════════════════════════════════════════════════
#  6. should_remove_by_id()
# ═══════════════════════════════════════════════════════════════════════════

class TestShouldRemoveById:

    def test_exact_noise_id_match(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_id("cookie") is True
        assert opts.should_remove_by_id("popup") is True
        assert opts.should_remove_by_id("modal") is True
        assert opts.should_remove_by_id("overlay") is True
        assert opts.should_remove_by_id("ad") is True
        assert opts.should_remove_by_id("ads") is True
        assert opts.should_remove_by_id("sidebar") is True
        assert opts.should_remove_by_id("newsletter") is True
        assert opts.should_remove_by_id("comments") is True

    def test_partial_id_match(self):
        """IDs use substring matching (any noise_id in id_lower)."""
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_id("main-ad-banner") is True
        assert opts.should_remove_by_id("cookie-consent") is True
        assert opts.should_remove_by_id("my-popup-123") is True

    def test_no_match(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_id("content") is False
        assert opts.should_remove_by_id("main") is False
        assert opts.should_remove_by_id("wrapper") is False

    def test_empty_id(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_id("") is False

    def test_none_id(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_id(None) is False

    def test_remove_ads_disabled(self):
        opts = MarkdownOptions(remove_ads=False)
        assert opts.should_remove_by_id("ad") is False
        assert opts.should_remove_by_id("cookie") is False

    def test_case_insensitive(self):
        opts = MarkdownOptions(remove_ads=True)
        assert opts.should_remove_by_id("COOKIE") is True
        assert opts.should_remove_by_id("POPUP") is True


# ═══════════════════════════════════════════════════════════════════════════
#  7. with_overrides()
# ═══════════════════════════════════════════════════════════════════════════

class TestWithOverrides:

    def test_returns_new_instance(self):
        opts = MarkdownOptions()
        new_opts = opts.with_overrides(remove_nav=False)
        assert new_opts is not opts

    def test_override_single_field(self):
        opts = MarkdownOptions()
        new_opts = opts.with_overrides(remove_nav=False)
        assert new_opts.remove_nav is False
        assert opts.remove_nav is True  # original unchanged

    def test_override_multiple_fields(self):
        opts = MarkdownOptions()
        new_opts = opts.with_overrides(
            remove_nav=False,
            include_links=False,
            max_length=1000,
        )
        assert new_opts.remove_nav is False
        assert new_opts.include_links is False
        assert new_opts.max_length == 1000
        # Original unchanged
        assert opts.remove_nav is True
        assert opts.include_links is True
        assert opts.max_length == 100000

    def test_override_preserves_other_fields(self):
        opts = MarkdownOptions(max_length=5000, include_images=True)
        new_opts = opts.with_overrides(remove_nav=False)
        assert new_opts.max_length == 5000
        assert new_opts.include_images is True

    def test_chained_overrides(self):
        opts = MarkdownOptions()
        step1 = opts.with_overrides(remove_nav=False)
        step2 = step1.with_overrides(include_links=False)
        step3 = step2.with_overrides(max_length=999)
        assert step3.remove_nav is False
        assert step3.include_links is False
        assert step3.max_length == 999
        # Original unchanged
        assert opts.remove_nav is True
        assert opts.include_links is True
        assert opts.max_length == 100000


# ═══════════════════════════════════════════════════════════════════════════
#  8. COMMON_NOISE_PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

class TestCommonNoisePatterns:

    def test_is_list(self):
        assert isinstance(COMMON_NOISE_PATTERNS, list)

    def test_non_empty(self):
        assert len(COMMON_NOISE_PATTERNS) > 0

    def test_all_valid_regex(self):
        import re
        for pattern in COMMON_NOISE_PATTERNS:
            re.compile(pattern)  # should not raise

    def test_patterns_match_expected_content(self):
        import re
        # Timestamp pattern
        assert any(
            re.search(p, "posted 3 days ago", re.IGNORECASE)
            for p in COMMON_NOISE_PATTERNS
        )
        # Apply now
        assert any(
            re.search(p, "Apply Now", re.IGNORECASE)
            for p in COMMON_NOISE_PATTERNS
        )
        # View count
        assert any(
            re.search(p, "150 applicants", re.IGNORECASE)
            for p in COMMON_NOISE_PATTERNS
        )


# ═══════════════════════════════════════════════════════════════════════════
#  9. Pydantic model behavior
# ═══════════════════════════════════════════════════════════════════════════

class TestModelBehavior:

    def test_validate_assignment(self):
        """validate_assignment=True should catch invalid updates."""
        opts = MarkdownOptions()
        opts.max_length = 5000
        assert opts.max_length == 5000

    def test_validate_assignment_negative_rejected(self):
        opts = MarkdownOptions()
        with pytest.raises(Exception):
            opts.max_length = -1

    def test_model_dump(self):
        opts = MarkdownOptions()
        data = opts.model_dump()
        assert isinstance(data, dict)
        assert data["remove_nav"] is True
        assert data["include_links"] is True

    def test_not_frozen(self):
        """Model should NOT be frozen (frozen=False)."""
        opts = MarkdownOptions()
        opts.remove_nav = False
        assert opts.remove_nav is False

    def test_frozenset_fields_not_mutated_in_place(self):
        """noise_tags etc. are frozenset — cannot add/remove in place."""
        opts = MarkdownOptions()
        with pytest.raises(AttributeError):
            opts.noise_tags.add("new_tag")
