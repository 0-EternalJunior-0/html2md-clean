from __future__ import annotations

import csv
import gc
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

SIZES = list(range(100_000, 500_001, 100_000))
RUNS = 3
TIMEOUT_SECONDS = 180
ROOT = Path(__file__).resolve().parents[1]

def generate_html(target_chars: int) -> str:
    prefix = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Large benchmark document</title>
<style>
body { font-family: Arial, sans-serif; }
.ad { display: none; }
.cookie-banner { position: fixed; }
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
<a href="https://example.com/test">Example link</a>.
</p>
<p>
A second paragraph contains
<strong>bold text</strong>,
<em>italic text</em>,
<code>inline code</code>,
and another
<a href="https://example.com/jobs">link to a page</a>.
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
<p>Related content that should remain part of the document.</p>
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
    html = prefix
    while len(html) + len(repeated_block) + len(suffix) < target_chars:
        html += repeated_block
    html += suffix
    return html

def convert_ours(html: str) -> str:
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

def convert_html_to_markdown(html: str) -> str:
    from html_to_markdown import convert
    result = convert(html)
    if isinstance(result, dict):
        return str(result.get("content", ""))
    content = getattr(result, "content", None)
    if content is not None:
        return str(content)
    return str(result)

def convert_markdownify(html: str) -> str:
    from markdownify import markdownify
    return markdownify(html)

def convert_html2text(html: str) -> str:
    import html2text
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.body_width = 0
    return converter.handle(html)

def convert_html2md(html: str) -> str:
    import html2md
    return html2md.convert(html)


def convert_trafilatura(html: str) -> str:
    import trafilatura
    result = trafilatura.extract(
        html,
        output_format="markdown",
        include_links=True,
        include_images=False,
    )
    return result or ""

CONVERTERS = {
    "OUR html2md-clean": convert_ours,
    "html-to-markdown": convert_html_to_markdown,
    "markdownify": convert_markdownify,
    "html2text": convert_html2text,
    "html2md": convert_html2md,
    "trafilatura": convert_trafilatura,
}

def worker(library: str, html_file: str) -> None:
    import psutil
    process = psutil.Process(os.getpid())
    html = Path(html_file).read_text(encoding="utf-8")
    converter = CONVERTERS[library]
    converter(html)
    gc.collect()
    rss_before = process.memory_info().rss
    start = time.perf_counter()
    output = converter(html)
    elapsed = time.perf_counter() - start
    rss_after = process.memory_info().rss
    print(f"{elapsed:.9f}|{rss_before}|{rss_after}|{len(output)}")

def run_single(library: str, html: str) -> dict:
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
        if completed.returncode != 0:
            error = completed.stderr.strip() or completed.stdout.strip()
            return {
                "success": False,
                "error": error[-4000:],
            }
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
        parts = lines[-1].split("|")
        if len(parts) != 4:
            return {
                "success": False,
                "error": "Invalid worker output:\n" + completed.stdout[-4000:],
            }
        return {
            "success": True,
            "time": float(parts[0]),
            "rss_before": int(parts[1]),
            "rss_after": int(parts[2]),
            "output_size": int(parts[3]),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"TIMEOUT: conversion exceeded {TIMEOUT_SECONDS} seconds",
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

def format_mb(value: int | float) -> str:
    return f"{value / 1024 / 1024:.1f} MB"

def format_size(value: int | float) -> str:
    return f"{value:,.0f}"

def print_header() -> None:
    print()
    print("=" * 120)
    print("HTML → MARKDOWN BENCHMARK")
    print("=" * 120)
    print()
    print(f"Python: {sys.version.split()[0]}")
    print(f"Runs per library: {RUNS}")
    print(f"Timeout: {TIMEOUT_SECONDS}s")
    print(f"Sizes: {', '.join(f'{size // 1000}k' for size in SIZES)}")
    print()
    print("Libraries:")
    for name in CONVERTERS:
        print(f"  - {name}")
    print()

def print_results(size: int, results: dict[str, dict]) -> None:
    print()
    print("=" * 120)
    print(
        f"INPUT: {size:,} target chars "
        f"({size / 1024 / 1024:.2f} MB target)"
    )
    print("=" * 120)
    print(
        f"{'Library':<26}"
        f"{'Time':>12}"
        f"{'RAM':>14}"
        f"{'Output':>16}"
        f"{'Speed':>15}"
        f"{'Status':>12}"
    )
    print("-" * 120)
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
            error = result.get("error", "Unknown error")
            if error:
                print(f"    ERROR: {error}")
            continue
        time_sec = result["time"]
        ram = max(
            result["rss_before"],
            result["rss_after"],
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
    print("-" * 120)

class BenchmarkDashboard:
    def __init__(self, libraries: list[str]) -> None:
        self.libraries = libraries
        self.data = {
            library: {
                "sizes": [],
                "time": [],
                "ram": [],
                "speed": [],
                "output": [],
                "success": [],
            }
            for library in libraries
        }
        self.enabled = MATPLOTLIB_AVAILABLE
        if not self.enabled:
            print(
                "\nWARNING: matplotlib is not installed. "
                "Live graphs are disabled.\n"
            )
            return
        plt.ion()
        self.fig, self.axes = plt.subplots(
            2,
            3,
            figsize=(18, 10),
        )
        try:
            self.fig.canvas.manager.set_window_title(
                "HTML → Markdown Benchmark"
            )
        except Exception:
            pass
        self.fig.suptitle(
            "HTML → Markdown Benchmark — Live Results",
            fontsize=18,
            fontweight="bold",
        )
        self.ax_time = self.axes[0][0]
        self.ax_ram = self.axes[0][1]
        self.ax_speed = self.axes[0][2]
        self.ax_output = self.axes[1][0]
        self.ax_relative = self.axes[1][1]
        self.ax_success = self.axes[1][2]

    def update(self, size: int, results: dict[str, dict]) -> None:
        if not self.enabled:
            return
        for library, result in results.items():
            existing_sizes = self.data[library]["sizes"]
            if size in existing_sizes:
                index = existing_sizes.index(size)
                for key in [
                    "time",
                    "ram",
                    "speed",
                    "output",
                    "success",
                ]:
                    self.data[library][key].pop(index)
                existing_sizes.pop(index)
            self.data[library]["sizes"].append(size)
            if not result["success"]:
                self.data[library]["time"].append(math.nan)
                self.data[library]["ram"].append(math.nan)
                self.data[library]["speed"].append(math.nan)
                self.data[library]["output"].append(math.nan)
                self.data[library]["success"].append(0)
                continue
            time_sec = result["time"]
            ram_mb = max(
                result["rss_before"],
                result["rss_after"],
            ) / 1024 / 1024
            speed = (
                size / 1024 / 1024 / time_sec
                if time_sec > 0
                else 0
            )
            output_mb = (
                    result["output_size"]
                    / 1024
                    / 1024
            )
            self.data[library]["time"].append(time_sec)
            self.data[library]["ram"].append(ram_mb)
            self.data[library]["speed"].append(speed)
            self.data[library]["output"].append(output_mb)
            self.data[library]["success"].append(1)
        self.redraw(size)

    def redraw(self, current_size: int) -> None:
        if not self.enabled:
            return
        axes = [
            self.ax_time,
            self.ax_ram,
            self.ax_speed,
            self.ax_output,
            self.ax_relative,
            self.ax_success,
        ]
        for ax in axes:
            ax.clear()

        for library in self.libraries:
            data = self.data[library]
            self.ax_time.plot(
                data["sizes"],
                data["time"],
                marker="o",
                linewidth=2,
                label=library,
            )
        self.ax_time.set_title("Execution Time")
        self.ax_time.set_xlabel("Input size")
        self.ax_time.set_ylabel("Seconds")
        self.ax_time.grid(True, alpha=0.3)
        self.ax_time.legend(fontsize=8)

        for library in self.libraries:
            data = self.data[library]
            self.ax_ram.plot(
                data["sizes"],
                data["ram"],
                marker="o",
                linewidth=2,
                label=library,
            )
        self.ax_ram.set_title("Peak RSS Memory")
        self.ax_ram.set_xlabel("Input size")
        self.ax_ram.set_ylabel("RAM (MB)")
        self.ax_ram.grid(True, alpha=0.3)
        self.ax_ram.legend(fontsize=8)

        for library in self.libraries:
            data = self.data[library]
            self.ax_speed.plot(
                data["sizes"],
                data["speed"],
                marker="o",
                linewidth=2,
                label=library,
            )
        self.ax_speed.set_title("Throughput")
        self.ax_speed.set_xlabel("Input size")
        self.ax_speed.set_ylabel("MB/s")
        self.ax_speed.grid(True, alpha=0.3)
        self.ax_speed.legend(fontsize=8)

        for library in self.libraries:
            data = self.data[library]
            self.ax_output.plot(
                data["sizes"],
                data["output"],
                marker="o",
                linewidth=2,
                label=library,
            )
        self.ax_output.set_title("Markdown Output Size")
        self.ax_output.set_xlabel("Input size")
        self.ax_output.set_ylabel("Output (MB)")
        self.ax_output.grid(True, alpha=0.3)
        self.ax_output.legend(fontsize=8)

        our_data = self.data["OUR html2md-clean"]
        our_times_by_size = dict(
            zip(
                our_data["sizes"],
                our_data["time"],
            )
        )
        for library in self.libraries:
            if library == "OUR html2md-clean":
                continue
            data = self.data[library]
            relative = []
            for size, time_value in zip(
                    data["sizes"],
                    data["time"],
            ):
                our_time = our_times_by_size.get(
                    size,
                    math.nan,
                )
                if (
                        math.isnan(time_value)
                        or math.isnan(our_time)
                        or our_time <= 0
                ):
                    relative.append(math.nan)
                else:
                    relative.append(
                        time_value / our_time
                    )
            self.ax_relative.plot(
                data["sizes"],
                relative,
                marker="o",
                linewidth=2,
                label=library,
            )
        self.ax_relative.axhline(
            1.0,
            linestyle="--",
            linewidth=1.5,
        )
        self.ax_relative.set_title(
            "Relative Time vs OUR html2md-clean"
        )
        self.ax_relative.set_xlabel("Input size")
        self.ax_relative.set_ylabel("Multiplier")
        self.ax_relative.grid(True, alpha=0.3)
        self.ax_relative.legend(fontsize=8)

        for library in self.libraries:
            data = self.data[library]
            values = [
                value * 100
                for value in data["success"]
            ]
            self.ax_success.plot(
                data["sizes"],
                values,
                marker="o",
                linewidth=2,
                label=library,
            )
        self.ax_success.set_title("Success Rate")
        self.ax_success.set_xlabel("Input size")
        self.ax_success.set_ylabel("Success (%)")
        self.ax_success.set_ylim(-5, 105)
        self.ax_success.grid(True, alpha=0.3)
        self.ax_success.legend(fontsize=8)

        for ax in axes:
            ax.set_xticks(SIZES)
            ax.set_xticklabels(
                [f"{size // 1000}k" for size in SIZES],
                rotation=45,
            )

        self.fig.suptitle(
            f"HTML → Markdown Benchmark — Current: {current_size // 1000}k",
            fontsize=18,
            fontweight="bold",
        )
        self.fig.tight_layout(
            rect=[0, 0, 1, 0.95]
        )
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.01)

    def save(self) -> None:
        if not self.enabled:
            return
        output = ROOT / "benchmark_dashboard.png"
        self.fig.savefig(
            output,
            dpi=160,
            bbox_inches="tight",
        )
        print(f"\nDashboard saved to:\n{output}")

    def show(self) -> None:
        if not self.enabled:
            return
        plt.ioff()
        plt.show()

def save_results_json(all_results: dict) -> None:
    output = ROOT / "benchmark_results.json"
    with output.open("w", encoding="utf-8") as f:
        json.dump(
            all_results,
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"JSON results saved to:\n{output}")

def save_results_csv(all_results: dict) -> None:
    output = ROOT / "benchmark_results.csv"
    rows = []

    for target_size, results in all_results.items():
        target_size = int(target_size)

        for library, result in results.items():
            if not result["success"]:
                rows.append({
                    "input_chars": target_size,
                    "input_kb": target_size / 1000,
                    "library": library,
                    "success": False,
                    "time_sec": "",
                    "ram_mb": "",
                    "output_mb": "",
                    "throughput_mb_s": "",
                })
                continue

            ram = max(result["rss_before"],result["rss_after"])

            throughput = (
                    target_size
                    / 1024
                    / 1024
                    / result["time"]
            )

            rows.append({
                "input_chars": target_size,
                "input_kb": target_size / 1000,
                "library": library,
                "success": True,
                "time_sec": result["time"],
                "ram_mb": ram / 1024 / 1024,
                "output_mb": result["output_size"] / 1024 / 1024,
                "throughput_mb_s": throughput,
            })

    with output.open("w",newline="",encoding="utf-8") as f:
        writer = csv.DictWriter(f,
            fieldnames=[
                "input_chars",
                "input_kb",
                "library",
                "success",
                "time_sec",
                "ram_mb",
                "output_mb",
                "throughput_mb_s",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"CSV results saved to:\n{output}")

def benchmark() -> None:
    print_header()
    dashboard = BenchmarkDashboard(list(CONVERTERS.keys()))
    all_results = {}

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
            result = None

            for run_number in range(RUNS):
                result = run_single(
                    library,
                    html,
                )
                if not result["success"]:
                    runs = []
                    break
                runs.append(result)

            if not runs:
                results[library] = result
                print("FAILED")
                dashboard.update(
                    actual_size,
                    {library: result},
                )
                continue

            measured_runs = runs[1:] if len(runs) > 1 else runs

            avg_time = (
                    sum(item["time"] for item in measured_runs)
                    / len(measured_runs)
            )
            avg_rss_before = (
                    sum(item["rss_before"] for item in measured_runs)
                    / len(measured_runs)
            )
            avg_rss_after = (
                    sum(item["rss_after"] for item in measured_runs)
                    / len(measured_runs)
            )
            avg_output_size = (
                    sum(item["output_size"] for item in measured_runs)
                    / len(measured_runs)
            )

            results[library] = {
                "success": True,
                "time": avg_time,
                "rss_before": int(avg_rss_before),
                "rss_after": int(avg_rss_after),
                "output_size": int(avg_output_size),
            }

            print(f"{avg_time:.3f}s")

            dashboard.update(actual_size,{library: results[library]})

        print_results(actual_size,results)

        all_results[str(target_size)] = results

    save_results_json(all_results)
    save_results_csv(all_results)
    dashboard.save()
    dashboard.show()

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--worker":
        worker(
            sys.argv[2],
            sys.argv[3],
        )
    else:
        benchmark()