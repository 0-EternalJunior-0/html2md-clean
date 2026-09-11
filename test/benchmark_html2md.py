from __future__ import annotations

import re
import sys
import json
import time
import gc
import subprocess
import tempfile
import os
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

# Change this if test3.html is located somewhere else.
TEST_HTML = ROOT / "test/data/test3.html"

RESULTS_DIR = ROOT / "test_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Our html2md-clean
# ============================================================

def convert_ours(html: str) -> str:
    """Our html2md-clean implementation."""

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from markdown.generator import MarkdownGenerator
    from markdown.options import MarkdownOptions

    options = MarkdownOptions(
        include_links=False,
        include_images=False,

        remove_nav=False,
        remove_footer=True,
        remove_ads=True,
        remove_scripts=True,
        remove_header=False,
        remove_aside=False,
        remove_buttons=True,
        remove_forms=False,

        min_paragraph_length=5,
        min_heading_length=1,

        preserve_inline_formatting=True,
        normalize_whitespace=True,
        preserve_whitespace=False,

        generate_citations=True,
        use_content_density=False,
        link_density_threshold=0.6,
        min_content_words=20,

        link_style="inline",

        noise_classes=frozenset({
            "ad",
            "ads",
            "advertisement",
            "banner",
            "cookie",
            "popup",
            "modal",
            "overlay",
            "newsletter",
            "subscribe",
            "social",
            "share",
            "sponsored",
            "carousel",
            "promo",
            "disclaimer",
        }),

        noise_tags=frozenset({
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "canvas",
            "iframe",
            "embed",
            "object",
        }),

        noise_ids=frozenset({
            "cookie",
            "popup",
            "modal",
            "overlay",
            "newsletter",
            "ads",
        }),

        include_tables=True,
        include_lists=True,
        include_blockquotes=True,
        include_code_blocks=True,

        max_length=200_000_000,

        extract_div_text=True,
        force_beautifulsoup=False,

        dynamic_noise_patterns=[],
    )

    generator = MarkdownGenerator(options)

    result = generator.generate_from_html(html)

    return result.fit_markdown


# ============================================================
# Other converters
# ============================================================

def convert_html_to_markdown(html: str) -> str:
    """html-to-markdown."""

    from html_to_markdown import convert

    result = convert(html)

    if isinstance(result, dict):
        return str(result.get("content", ""))

    content = getattr(result, "content", None)

    if content is not None:
        return str(content)

    return str(result)


def convert_markdownify(html: str) -> str:
    """markdownify."""

    from markdownify import markdownify

    return markdownify(html)


def convert_html2text(html: str) -> str:
    """html2text."""

    import html2text

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.body_width = 0

    return converter.handle(html)


def convert_html2md(html: str) -> str:
    """html2md."""

    import html2md

    return html2md.convert(html)


def convert_trafilatura(html: str) -> str:
    """trafilatura."""

    import trafilatura

    result = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=True,
        include_images=False,
    )

    return result or ""


# ============================================================
# Registry
# ============================================================

CONVERTERS = {
    "OUR html2md-clean": convert_ours,
    "html-to-markdown": convert_html_to_markdown,
    "markdownify": convert_markdownify,
    "html2text": convert_html2text,
    "html2md": convert_html2md,
    "trafilatura": convert_trafilatura,
}


# ============================================================
# HTML analyzer
# ============================================================

class HTMLAnalyzer(HTMLParser):
    """
    Extract structural information from the original HTML.

    This is used as a reference to compare Markdown outputs.
    """

    NOISE_TAGS = {
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "canvas",
        "iframe",
        "embed",
        "object",
    }

    def __init__(self):
        super().__init__()

        self.text_parts = []

        self.headings = Counter()
        self.links = 0
        self.images = 0
        self.tables = 0
        self.table_rows = 0
        self.lists = 0
        self.list_items = 0
        self.blockquotes = 0
        self.code_blocks = 0
        self.paragraphs = 0

        self.tag_stack = []
        self.in_noise = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        self.tag_stack.append(tag)

        if tag in self.NOISE_TAGS:
            self.in_noise += 1

        if self.in_noise:
            return

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.headings[tag] += 1

        elif tag == "a":
            self.links += 1

        elif tag == "img":
            self.images += 1

        elif tag == "table":
            self.tables += 1

        elif tag == "tr":
            self.table_rows += 1

        elif tag in {"ul", "ol"}:
            self.lists += 1

        elif tag == "li":
            self.list_items += 1

        elif tag == "blockquote":
            self.blockquotes += 1

        elif tag == "pre":
            self.code_blocks += 1

        elif tag == "p":
            self.paragraphs += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

        if self.tag_stack:
            self.tag_stack.pop()

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag in self.NOISE_TAGS and self.in_noise:
            self.in_noise -= 1

        if self.tag_stack:
            self.tag_stack.pop()

    def handle_data(self, data):
        if self.in_noise:
            return

        text = re.sub(r"\s+", " ", data).strip()

        if text:
            self.text_parts.append(text)

    def result(self):
        text = " ".join(self.text_parts)
        text = normalize_text(text)

        return {
            "text": text,
            "chars": len(text),
            "words": count_words(text),
            "unique_words": count_unique_words(text),

            "headings": dict(self.headings),
            "links": self.links,
            "images": self.images,
            "tables": self.tables,
            "table_rows": self.table_rows,
            "lists": self.lists,
            "list_items": self.list_items,
            "blockquotes": self.blockquotes,
            "code_blocks": self.code_blocks,
            "paragraphs": self.paragraphs,
        }


# ============================================================
# Text helpers
# ============================================================

WORD_RE = re.compile(
    r"[^\W\d_]+(?:['’-][^\W\d_]+)*",
    re.UNICODE,
)


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def count_words(text: str) -> int:
    return len(get_words(text))


def count_unique_words(text: str) -> int:
    return len(set(get_words(text)))


def top_words(text: str, limit: int = 10):
    words = get_words(text)

    return Counter(words).most_common(limit)


def longest_words(text: str, limit: int = 10):
    words = set(get_words(text))

    return sorted(
        words,
        key=lambda word: (-len(word), word),
    )[:limit]


def count_sentences(text: str) -> int:
    if not text.strip():
        return 0

    sentences = re.split(
        r"(?<=[.!?])\s+",
        normalize_text(text),
    )

    return len([x for x in sentences if x.strip()])


def count_paragraphs_markdown(md: str) -> int:
    blocks = re.split(r"\n\s*\n", md.strip())

    return len([
        block
        for block in blocks
        if block.strip()
    ])


def count_markdown_headings(md: str):
    result = Counter()

    for line in md.splitlines():
        match = re.match(r"^(#{1,6})\s+", line.strip())

        if match:
            level = len(match.group(1))
            result[f"h{level}"] += 1

    return dict(result)


def count_markdown_links(md: str) -> int:
    return len(
        re.findall(
            r"\[[^\]]+\]\([^)]+\)",
            md,
        )
    )


def count_markdown_images(md: str) -> int:
    return len(
        re.findall(
            r"!\[[^\]]*\]\([^)]+\)",
            md,
        )
    )


def count_markdown_lists(md: str) -> int:
    return len(
        re.findall(
            r"(?m)^\s*(?:[-*+]|\d+\.)\s+",
            md,
        )
    )


def count_markdown_code_blocks(md: str) -> int:
    return len(
        re.findall(
            r"(?ms)```.*?```",
            md,
        )
    )


def count_markdown_blockquotes(md: str) -> int:
    return len(
        re.findall(
            r"(?m)^\s*>\s+",
            md,
        )
    )


def count_tables_markdown(md: str) -> int:
    lines = md.splitlines()

    count = 0

    for i in range(len(lines) - 1):
        current = lines[i].strip()
        next_line = lines[i + 1].strip()

        if (
                "|" in current
                and re.match(
            r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$",
            next_line,
        )
        ):
            count += 1

    return count


# ============================================================
# Noise detection
# ============================================================

NOISE_PATTERNS = [
    r"cookie",
    r"advertisement",
    r"\bad\b",
    r"\bads\b",
    r"newsletter",
    r"subscribe",
    r"tracking",
    r"analytics",
    r"privacy policy",
]


def detect_noise(md: str) -> list[str]:
    found = []

    lower = md.lower()

    for pattern in NOISE_PATTERNS:
        if re.search(pattern, lower):
            found.append(pattern)

    return found


# ============================================================
# Text similarity
# ============================================================

def word_counter(text: str):
    return Counter(get_words(text))


def calculate_text_retention(original_text: str, markdown: str) -> float:
    """
    Approximate percentage of original visible words
    retained in Markdown.

    Uses word frequency rather than raw string matching,
    because Markdown adds syntax around the text.
    """

    original = word_counter(original_text)
    output = word_counter(markdown)

    if not original:
        return 100.0

    original_total = sum(original.values())

    matched = 0

    for word, count in original.items():
        matched += min(
            count,
            output.get(word, 0),
        )

    return matched / original_total * 100


def calculate_text_loss(original_text: str, markdown: str) -> float:
    return max(
        0.0,
        100.0 - calculate_text_retention(
            original_text,
            markdown,
        ),
        )


# ============================================================
# Structural comparison
# ============================================================

def compare_structure(reference: dict, markdown: str):
    md_headings = count_markdown_headings(markdown)

    expected_headings = reference["headings"]

    heading_expected = sum(
        expected_headings.values()
    )

    heading_actual = sum(
        md_headings.values()
    )

    if heading_expected:
        heading_score = min(
            heading_actual / heading_expected,
            1.0,
            ) * 100
    else:
        heading_score = 100.0

    def ratio(actual, expected):
        if expected == 0:
            return 100.0

        return min(
            actual / expected,
            1.0,
            ) * 100

    return {
        "heading_score": heading_score,

        "headings_expected": heading_expected,
        "headings_actual": heading_actual,

        "links_expected": reference["links"],
        "links_actual": count_markdown_links(markdown),

        "images_expected": reference["images"],
        "images_actual": count_markdown_images(markdown),

        "lists_expected": reference["list_items"],
        "lists_actual": count_markdown_lists(markdown),

        "tables_expected": reference["tables"],
        "tables_actual": count_tables_markdown(markdown),

        "code_expected": reference["code_blocks"],
        "code_actual": count_markdown_code_blocks(markdown),

        "blockquotes_expected": reference["blockquotes"],
        "blockquotes_actual": count_markdown_blockquotes(markdown),

        "list_score": ratio(
            count_markdown_lists(markdown),
            reference["list_items"],
        ),

        "table_score": ratio(
            count_tables_markdown(markdown),
            reference["tables"],
        ),

        "code_score": ratio(
            count_markdown_code_blocks(markdown),
            reference["code_blocks"],
        ),

        "blockquote_score": ratio(
            count_markdown_blockquotes(markdown),
            reference["blockquotes"],
        ),
    }


# ============================================================
# Quality score
# ============================================================

def calculate_quality_score(
        text_retention: float,
        structure: dict,
        noise_count: int,
) -> float:

    structure_scores = [
        structure["heading_score"],
        structure["list_score"],
        structure["table_score"],
        structure["code_score"],
        structure["blockquote_score"],
    ]

    structure_score = sum(
        structure_scores
    ) / len(structure_scores)

    noise_score = 100.0

    if noise_count:
        noise_score = max(
            0.0,
            100.0 - noise_count * 15.0,
            )

    score = (
            text_retention * 0.50
            + structure_score * 0.35
            + noise_score * 0.15
    )

    return round(
        min(100.0, max(0.0, score)),
        2,
    )


# ============================================================
# Analyze Markdown
# ============================================================

def analyze_markdown(
        markdown: str,
        reference: dict,
        elapsed: float,
):
    text = strip_markdown(markdown)

    words = get_words(text)

    retention = calculate_text_retention(
        reference["text"],
        text,
    )

    structure = compare_structure(
        reference,
        markdown,
    )

    noise = detect_noise(markdown)

    quality = calculate_quality_score(
        retention,
        structure,
        len(noise),
    )

    return {
        "output_chars": len(markdown),
        "text_chars": len(text),

        "words": len(words),
        "unique_words": len(set(words)),

        "sentences": count_sentences(text),
        "paragraphs": count_paragraphs_markdown(markdown),

        "headings": count_markdown_headings(markdown),
        "links": count_markdown_links(markdown),
        "images": count_markdown_images(markdown),
        "lists": count_markdown_lists(markdown),
        "tables": count_tables_markdown(markdown),
        "code_blocks": count_markdown_code_blocks(markdown),
        "blockquotes": count_markdown_blockquotes(markdown),

        "text_retention_percent": round(
            retention,
            2,
        ),

        "text_loss_percent": round(
            100.0 - retention,
            2,
            ),

        "noise_detected": noise,
        "noise_count": len(noise),

        "quality_score": quality,

        "time_seconds": round(
            elapsed,
            6,
        ),

        "longest_words": [
            {
                "word": word,
                "length": len(word),
            }
            for word in longest_words(
                text,
                10,
            )
        ],

        "top_words": [
            {
                "word": word,
                "count": count,
            }
            for word, count in top_words(
                text,
                10,
            )
        ],

        "structure": structure,
    }


# ============================================================
# Strip Markdown syntax
# ============================================================

def strip_markdown(md: str) -> str:
    text = md

    # Images
    text = re.sub(
        r"!\[([^\]]*)\]\([^)]+\)",
        r"\1",
        text,
    )

    # Links
    text = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        text,
    )

    # Reference links
    text = re.sub(
        r"\[([^\]]+)\]\[[^\]]*\]",
        r"\1",
        text,
    )

    # Headings
    text = re.sub(
        r"(?m)^\s*#{1,6}\s+",
        "",
        text,
    )

    # Blockquotes
    text = re.sub(
        r"(?m)^\s*>\s?",
        "",
        text,
    )

    # Fenced code markers
    text = re.sub(
        r"```[a-zA-Z0-9_-]*",
        "",
        text,
    )

    text = text.replace(
        "```",
        "",
    )

    # Bold / italic / strike
    text = re.sub(
        r"(\*\*|__)(.*?)\1",
        r"\2",
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"(\*|_)(.*?)\1",
        r"\2",
        text,
        flags=re.DOTALL,
    )

    text = re.sub(
        r"~~(.*?)~~",
        r"\1",
        text,
        flags=re.DOTALL,
    )

    # Inline code
    text = re.sub(
        r"`([^`]+)`",
        r"\1",
        text,
    )

    # List markers
    text = re.sub(
        r"(?m)^\s*(?:[-*+]|\d+\.)\s+",
        "",
        text,
    )

    return normalize_text(text)


# ============================================================
# Run converter
# ============================================================

def run_converter(
        name: str,
        converter,
        html: str,
):
    print(
        f"  Testing {name}...",
        end=" ",
        flush=True,
    )

    gc.collect()

    start = time.perf_counter()

    try:
        markdown = converter(html)

        elapsed = time.perf_counter() - start

    except Exception as exc:
        print("FAILED")

        return {
            "success": False,
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
        }

    if markdown is None:
        markdown = ""

    markdown = str(markdown)

    print(
        f"{elapsed:.3f}s"
    )

    return {
        "success": True,
        "markdown": markdown,
        "time": elapsed,
    }


# ============================================================
# Safe filename
# ============================================================

def safe_filename(name: str) -> str:
    return re.sub(
        r"[^a-zA-Z0-9_.-]+",
        "_",
        name,
    ).strip("_")


# ============================================================
# Print analysis
# ============================================================

def print_analysis(
        name: str,
        analysis: dict,
):
    print()
    print("=" * 100)
    print(name)
    print("=" * 100)

    print(
        f"Quality score:       {analysis['quality_score']:.2f}/100"
    )

    print(
        f"Conversion time:     {analysis['time_seconds']:.6f}s"
    )

    print()

    print(
        f"Output chars:         {analysis['output_chars']:,}"
    )

    print(
        f"Markdown text chars:  {analysis['text_chars']:,}"
    )

    print(
        f"Words:                {analysis['words']:,}"
    )

    print(
        f"Unique words:         {analysis['unique_words']:,}"
    )

    print(
        f"Sentences:            {analysis['sentences']:,}"
    )

    print(
        f"Paragraphs:            {analysis['paragraphs']:,}"
    )

    print()

    print(
        f"Text retention:       {analysis['text_retention_percent']:.2f}%"
    )

    print(
        f"Text loss:             {analysis['text_loss_percent']:.2f}%"
    )

    print()

    print("Structure:")

    structure = analysis["structure"]

    print(
        f"  Headings:            "
        f"{structure['headings_actual']}/"
        f"{structure['headings_expected']}"
    )

    print(
        f"  Lists:               "
        f"{structure['lists_actual']}/"
        f"{structure['lists_expected']}"
    )

    print(
        f"  Tables:              "
        f"{structure['tables_actual']}/"
        f"{structure['tables_expected']}"
    )

    print(
        f"  Code blocks:         "
        f"{structure['code_actual']}/"
        f"{structure['code_expected']}"
    )

    print(
        f"  Blockquotes:         "
        f"{structure['blockquotes_actual']}/"
        f"{structure['blockquotes_expected']}"
    )

    print()

    print("Longest words:")

    for index, item in enumerate(
            analysis["longest_words"],
            1,
    ):
        print(
            f"  {index:2}. "
            f"{item['word']} "
            f"({item['length']})"
        )

    print()

    print("Top 10 words:")

    for index, item in enumerate(
            analysis["top_words"],
            1,
    ):
        print(
            f"  {index:2}. "
            f"{item['word']} "
            f"({item['count']})"
        )

    print()

    if analysis["noise_detected"]:
        print(
            "Possible noise detected:"
        )

        for item in analysis["noise_detected"]:
            print(
                f"  - {item}"
            )

    else:
        print(
            "Possible noise detected: NONE"
        )


# ============================================================
# Summary table
# ============================================================

def print_summary(results: dict):
    print()
    print()
    print("=" * 120)
    print("FINAL COMPARISON")
    print("=" * 120)

    print(
        f"{'Library':<25}"
        f"{'Quality':>10}"
        f"{'Retention':>12}"
        f"{'Words':>12}"
        f"{'Output':>14}"
        f"{'Time':>12}"
    )

    print("-" * 120)

    successful = []

    for name, result in results.items():

        if not result["success"]:
            print(
                f"{name:<25}"
                f"{'FAILED':>10}"
            )
            continue

        analysis = result["analysis"]

        successful.append(
            (name, analysis)
        )

        print(
            f"{name:<25}"
            f"{analysis['quality_score']:>9.2f}"
            f"{analysis['text_retention_percent']:>11.2f}%"
            f"{analysis['words']:>12,}"
            f"{analysis['output_chars']:>14,}"
            f"{analysis['time_seconds']:>11.3f}s"
        )

    print("-" * 120)

    if successful:
        best = max(
            successful,
            key=lambda x: x[1]["quality_score"],
        )

        fastest = min(
            successful,
            key=lambda x: x[1]["time_seconds"],
        )

        retention = max(
            successful,
            key=lambda x: x[1]["text_retention_percent"],
        )

        print()
        print(
            f"BEST QUALITY:   {best[0]} "
            f"({best[1]['quality_score']:.2f}/100)"
        )

        print(
            f"BEST RETENTION:  {retention[0]} "
            f"({retention[1]['text_retention_percent']:.2f}%)"
        )

        print(
            f"FASTEST:         {fastest[0]} "
            f"({fastest[1]['time_seconds']:.3f}s)"
        )


# ============================================================
# Main benchmark
# ============================================================

def benchmark():
    print()
    print("=" * 100)
    print("HTML → MARKDOWN QUALITY BENCHMARK")
    print("=" * 100)

    print()

    print(
        f"HTML file: {TEST_HTML}"
    )

    if not TEST_HTML.exists():
        print()
        print(
            "ERROR: test3.html not found!"
        )
        print()
        print(
            f"Expected path:"
        )
        print(
            f"  {TEST_HTML}"
        )
        print()

        sys.exit(1)

    html = TEST_HTML.read_text(
        encoding="utf-8",
    )

    print(
        f"Input size: {len(html):,} chars "
        f"({len(html) / 1024 / 1024:.2f} MB)"
    )

    # --------------------------------------------------------
    # Analyze original HTML
    # --------------------------------------------------------

    print()
    print("Analyzing original HTML...")

    parser = HTMLAnalyzer()

    parser.feed(html)

    reference = parser.result()

    print(
        f"Visible text: {reference['chars']:,} chars"
    )

    print(
        f"Words: {reference['words']:,}"
    )

    print(
        f"Unique words: {reference['unique_words']:,}"
    )

    print(
        f"Paragraphs: {reference['paragraphs']:,}"
    )

    print(
        f"Headings: "
        f"{sum(reference['headings'].values())}"
    )

    print(
        f"Links: {reference['links']}"
    )

    print(
        f"Images: {reference['images']}"
    )

    print(
        f"Tables: {reference['tables']}"
    )

    print(
        f"Lists: {reference['lists']}"
    )

    print(
        f"List items: {reference['list_items']}"
    )

    print(
        f"Code blocks: {reference['code_blocks']}"
    )

    print(
        f"Blockquotes: {reference['blockquotes']}"
    )

    # --------------------------------------------------------
    # Run libraries
    # --------------------------------------------------------

    results = {}

    for name, converter in CONVERTERS.items():

        result = run_converter(
            name,
            converter,
            html,
        )

        if not result["success"]:
            results[name] = result
            continue

        markdown = result["markdown"]

        # Save Markdown
        filename = (
                safe_filename(name)
                + ".md"
        )

        output_path = (
                RESULTS_DIR / filename
        )

        output_path.write_text(
            markdown,
            encoding="utf-8",
        )

        analysis = analyze_markdown(
            markdown,
            reference,
            result["time"],
        )

        result["analysis"] = analysis

        results[name] = result

        print(
            f"    Output: "
            f"{len(markdown):,} chars"
        )

        print(
            f"    Quality: "
            f"{analysis['quality_score']:.2f}/100"
        )

    # --------------------------------------------------------
    # Detailed reports
    # --------------------------------------------------------

    for name, result in results.items():

        if not result["success"]:
            continue

        print_analysis(
            name,
            result["analysis"],
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(results)

    # --------------------------------------------------------
    # Save JSON report
    # --------------------------------------------------------

    json_results = {}

    for name, result in results.items():

        if not result["success"]:
            json_results[name] = {
                "success": False,
                "error": result.get(
                    "error",
                    "Unknown error",
                ),
            }

        else:
            json_results[name] = {
                "success": True,
                "analysis": result["analysis"],
                "markdown_file": str(
                    RESULTS_DIR
                    / (
                            safe_filename(name)
                            + ".md"
                    )
                ),
            }

    report_path = (
            RESULTS_DIR / "analysis.json"
    )

    report_path.write_text(
        json.dumps(
            {
                "input": {
                    "file": str(TEST_HTML),
                    "chars": len(html),
                    "reference": reference,
                },
                "results": json_results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("FILES")
    print("=" * 100)

    print(
        f"Results directory:"
    )

    print(
        f"  {RESULTS_DIR}"
    )

    print()

    for name, result in results.items():

        if result["success"]:
            print(
                f"  ✓ "
                f"{safe_filename(name)}.md"
            )

    print(
        "  ✓ analysis.json"
    )

    print()
    print("DONE.")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    benchmark()
