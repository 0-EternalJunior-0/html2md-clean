"""
HTML -> Markdown benchmark.

Compares:
1. OUR html2md-clean
2. html-to-markdown
3. markdownify
4. html2text
5. html2md
6. pyhtml2md
7. trafilatura

Measures:
- execution time
- RSS memory
- input size
- output size
- throughput
- success/failure

IMPORTANT:
- Every library receives the same HTML.
- HTML is NOT cut in the middle of a tag.
- Every library runs in a separate subprocess.
- First conversion is used as warm-up.
- Remaining runs are averaged.

Run:

    python test/benchmark_html2md.py

Install dependencies:

    python -m pip install html-to-markdown markdownify html2text html2md pyhtml2md trafilatura psutil
"""

from __future__ import annotations

import gc
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

SIZES = [
    100_000,       # ~100 KB
    500_000,       # ~500 KB
    1_000_000,     # ~1 MB
    2_000_000,     # ~2 MB
    5_000_000,     # ~5 MB
    10_000_000,    # ~10 MB
]

RUNS = 3

TIMEOUT_SECONDS = 180

ROOT = Path(__file__).resolve().parents[1]


# ============================================================
# HTML generator
# ============================================================

def generate_html(target_chars: int) -> str:
    """
    Generate a large but valid HTML document.

    Important:
    We never truncate HTML in the middle of a tag.

    The document contains:
    - headings
    - paragraphs
    - links
    - lists
    - tables
    - blockquotes
    - code
    - scripts
    - styles
    - navigation
    - ads
    - footer
    """

    prefix = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Large benchmark document</title>

    <style>
        body {
            font-family: Arial, sans-serif;
        }

        .ad {
            display: none;
        }

        .cookie-banner {
            position: fixed;
        }
    </style>

    <script>
        const trackingId = "benchmark";
        console.log(trackingId);
    </script>

    <script>
        function tracking() {
            return "analytics";
        }
    </script>
</head>

<body>

<header>
    <nav>
        <a href="/">Home</a>
        <a href="/jobs">Jobs</a>
        <a href="/about">About</a>
    </nav>
</header>

<main>
    <article>

        <h1>Large benchmark document</h1>

        <p>
            This is a benchmark document used to compare HTML to Markdown
            conversion libraries under identical workloads.
        </p>

        <h2>Introduction</h2>
"""

    repeated_block = """
        <section class="content-section">

            <h2>Section heading</h2>

            <p>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit.
                This paragraph contains realistic web content used to test
                HTML parsing, DOM traversal, whitespace normalization,
                Markdown generation, filtering, and memory usage.
                The document contains repeated structures so that the
                converter must process a realistic HTML tree.
                <a href="https://example.com/test">
                    Example link
                </a>.
            </p>

            <p>
                A second paragraph contains
                <strong>bold text</strong>,
                <em>italic text</em>,
                <code>inline code</code>,
                and another
                <a href="https://example.com/jobs">
                    link to a page
                </a>.
            </p>

            <blockquote>
                This is an important quotation inside the document.
            </blockquote>

            <ul>
                <li>First unordered item</li>
                <li>Second unordered item</li>
                <li>Third unordered item</li>
                <li>Fourth unordered item</li>
            </ul>

            <ol>
                <li>First ordered item</li>
                <li>Second ordered item</li>
                <li>Third ordered item</li>
            </ol>

            <pre><code class="language-python">
def example():
    value = 42
    return value
            </code></pre>

            <table>
                <thead>
                    <tr>
                        <th>Column</th>
                        <th>Value</th>
                    </tr>
                </thead>

                <tbody>
                    <tr>
                        <td>Name</td>
                        <td>Benchmark</td>
                    </tr>

                    <tr>
                        <td>Status</td>
                        <td>Active</td>
                    </tr>

                    <tr>
                        <td>Type</td>
                        <td>HTML</td>
                    </tr>
                </tbody>
            </table>

            <div class="related">
                <p>
                    Related content that should remain part of the document.
                </p>
            </div>

        </section>
"""

    suffix = """
    </article>
</main>

<aside class="ad">
    This is advertisement noise.
</aside>

<div class="cookie-banner">
    Cookie notification noise.
</div>

<footer>
    Footer noise.
</footer>

</body>
</html>
"""

    # Build complete HTML first.
    html = prefix

    # Add complete repeated blocks.
    while len(html) + len(repeated_block) + len(suffix) < target_chars:
        html += repeated_block

    html += suffix

    return html


# ============================================================
# Our converter
# ============================================================

def convert_ours(html: str) -> str:
    """
    Our html2md-clean implementation.
    """

    # Make project root importable.
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

        # Hard output limit.
        max_length=200_000_000,

        extract_div_text=True,
        force_beautifulsoup=False,

        dynamic_noise_patterns=[],
    )

    generator = MarkdownGenerator(options)

    result = generator.generate_from_html(html)

    return result.fit_markdown


# ============================================================
# html-to-markdown
# ============================================================

def convert_html_to_markdown(html: str) -> str:
    """
    html-to-markdown 3.x.

    The current API returns a ConversionResult-like object,
    which may expose content as a dictionary key or attribute.
    """

    from html_to_markdown import convert

    result = convert(html)

    # Possible dict-style result.
    if isinstance(result, dict):
        return str(result.get("content", ""))

    # Possible object-style result.
    content = getattr(result, "content", None)

    if content is not None:
        return str(content)

    # Fallback.
    return str(result)


# ============================================================
# markdownify
# ============================================================

def convert_markdownify(html: str) -> str:
    from markdownify import markdownify

    return markdownify(html)


# ============================================================
# html2text
# ============================================================

def convert_html2text(html: str) -> str:
    import html2text

    converter = html2text.HTML2Text()

    converter.ignore_links = False
    converter.body_width = 0

    return converter.handle(html)


# ============================================================
# html2md
# ============================================================

def convert_html2md(html: str) -> str:
    import html2md

    return html2md.convert(html)


# ============================================================


# ============================================================
# trafilatura
# ============================================================

def convert_trafilatura(html: str) -> str:
    import trafilatura

    result = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=True,
        include_images=False,
    )

    return result or ""


# ============================================================
# Converter registry
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
# Worker
# ============================================================

def worker(library: str, html_file: str) -> None:
    """
    Worker process.

    The conversion happens in a separate process so a bad library
    cannot crash the main benchmark.
    """

    import psutil

    process = psutil.Process(os.getpid())

    html = Path(html_file).read_text(
        encoding="utf-8"
    )

    converter = CONVERTERS[library]

    # --------------------------------------------------------
    # Warm-up
    # --------------------------------------------------------

    converter(html)

    gc.collect()

    # --------------------------------------------------------
    # Before benchmark
    # --------------------------------------------------------

    rss_before = process.memory_info().rss

    # --------------------------------------------------------
    # Actual benchmark
    # --------------------------------------------------------

    start = time.perf_counter()

    output = converter(html)

    elapsed = time.perf_counter() - start

    # --------------------------------------------------------
    # After benchmark
    # --------------------------------------------------------

    rss_after = process.memory_info().rss

    print(
        f"{elapsed:.9f}|"
        f"{rss_before}|"
        f"{rss_after}|"
        f"{len(output)}"
    )


# ============================================================
# Single run
# ============================================================

def run_single(library: str, html: str) -> dict:
    """
    Execute one benchmark run in a separate process.
    """

    html_file = None

    try:
        with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".html",
                delete=False,
                encoding="utf-8",
        ) as f:

            f.write(html)
            html_file = f.name

        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker",
            library,
            html_file,
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )

        # ----------------------------------------------------
        # Process failed
        # ----------------------------------------------------

        if completed.returncode != 0:

            error = completed.stderr.strip()

            if not error:
                error = completed.stdout.strip()

            return {
                "success": False,
                "error": error[-4000:],
            }

        # ----------------------------------------------------
        # Parse result
        # ----------------------------------------------------

        lines = [
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        ]

        if not lines:
            return {
                "success": False,
                "error": "Worker returned no output.",
            }

        line = lines[-1]

        parts = line.split("|")

        if len(parts) != 4:
            return {
                "success": False,
                "error": (
                        "Invalid worker output:\n"
                        + completed.stdout[-4000:]
                ),
            }

        elapsed = float(parts[0])
        rss_before = int(parts[1])
        rss_after = int(parts[2])
        output_size = int(parts[3])

        return {
            "success": True,
            "time": elapsed,
            "rss_before": rss_before,
            "rss_after": rss_after,
            "output_size": output_size,
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "error": (
                f"TIMEOUT: conversion exceeded "
                f"{TIMEOUT_SECONDS} seconds"
            ),
        }

    except Exception as exc:

        return {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    finally:

        if html_file:

            try:
                os.unlink(html_file)
            except OSError:
                pass


# ============================================================
# Helpers
# ============================================================

def format_mb(value: int | float) -> str:
    return f"{value / 1024 / 1024:.1f} MB"


def format_size(value: int | float) -> str:
    return f"{value:,.0f}"


# ============================================================
# Header
# ============================================================

def print_header() -> None:

    print()
    print("=" * 110)
    print("HTML → MARKDOWN BENCHMARK")
    print("=" * 110)
    print()

    print(f"Python: {sys.version.split()[0]}")
    print(f"Runs per library: {RUNS}")
    print(f"Timeout: {TIMEOUT_SECONDS}s")

    print()

    print("Libraries:")
    for name in CONVERTERS:
        print(f"  - {name}")

    print()


# ============================================================
# Result table
# ============================================================

def print_results(
        size: int,
        results: dict[str, dict],
) -> None:

    print()
    print("=" * 110)

    print(
        f"INPUT: "
        f"{len(str(size))} digit target / "
        f"{size:,} chars "
        f"({size / 1024 / 1024:.2f} MB)"
    )

    print("=" * 110)

    print(
        f"{'Library':<26}"
        f"{'Time':>12}"
        f"{'RAM':>14}"
        f"{'Output':>16}"
        f"{'Speed':>15}"
        f"{'Status':>12}"
    )

    print("-" * 110)

    for name, result in results.items():

        if not result["success"]:

            print(
                f"{name:<26}"
                f"{'ERROR':>12}"
                f"{'-':>14}"
                f"{'-':>16}"
                f"{'-':>15}"
                f"{'FAILED':>12}"
            )

            error = result.get(
                "error",
                "Unknown error",
            )

            if error:

                print()
                print("    ERROR:")

                for line in error.splitlines():
                    print(f"    {line}")

                print()

            continue

        time_sec = result["time"]

        rss_before = result["rss_before"]
        rss_after = result["rss_after"]

        # Use the larger observed RSS.
        ram = max(
            rss_before,
            rss_after,
        )

        output_size = result["output_size"]

        speed = (
            size / 1024 / 1024 / time_sec
            if time_sec > 0
            else 0
        )

        print(
            f"{name:<26}"
            f"{time_sec:>11.3f}s"
            f"{format_mb(ram):>14}"
            f"{format_size(output_size):>16}"
            f"{speed:>12.2f} MB/s"
            f"{'PASS':>12}"
        )

    print("-" * 110)


# ============================================================
# Benchmark
# ============================================================

def benchmark() -> None:

    print_header()

    for target_size in SIZES:

        html = generate_html(target_size)

        actual_size = len(html)

        print()
        print(
            f"Generating HTML: "
            f"{actual_size:,} chars "
            f"({actual_size / 1024 / 1024:.2f} MB)"
        )

        results = {}

        for library in CONVERTERS:

            print(
                f"  Testing {library}...",
                end=" ",
                flush=True,
            )

            runs = []

            for run_number in range(RUNS):

                result = run_single(
                    library,
                    html,
                )

                if not result["success"]:

                    # Save failure.
                    runs = []

                    break

                runs.append(result)

            # ------------------------------------------------
            # Failed library
            # ------------------------------------------------

            if not runs:

                results[library] = result

                print("FAILED")

                continue

            # ------------------------------------------------
            # Remove first run as warm-up
            # ------------------------------------------------

            if len(runs) > 1:
                measured_runs = runs[1:]
            else:
                measured_runs = runs

            # ------------------------------------------------
            # Average
            # ------------------------------------------------

            avg_time = (
                    sum(
                        item["time"]
                        for item in measured_runs
                    )
                    / len(measured_runs)
            )

            avg_rss_before = (
                    sum(
                        item["rss_before"]
                        for item in measured_runs
                    )
                    / len(measured_runs)
            )

            avg_rss_after = (
                    sum(
                        item["rss_after"]
                        for item in measured_runs
                    )
                    / len(measured_runs)
            )

            avg_output_size = (
                    sum(
                        item["output_size"]
                        for item in measured_runs
                    )
                    / len(measured_runs)
            )

            results[library] = {
                "success": True,
                "time": avg_time,
                "rss_before": int(avg_rss_before),
                "rss_after": int(avg_rss_after),
                "output_size": int(avg_output_size),
            }

            print(
                f"{avg_time:.3f}s"
            )

        print_results(
            actual_size,
            results,
        )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    # Worker mode.
    if (
            len(sys.argv) >= 4
            and sys.argv[1] == "--worker"
    ):

        worker(
            sys.argv[2],
            sys.argv[3],
        )

    # Normal benchmark mode.
    else:

        benchmark()