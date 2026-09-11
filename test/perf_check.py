"""Швидкий замір продуктивності конвертера (before/after правок аудиту).

Запуск: python test/perf_check.py
Міряє час конвертації test1.html та test3.html для Selectolax і BS4,
а також час lazy raw_markdown. Використовується для контролю регресій
під час впровадження правок аудиту.
"""
from __future__ import annotations

import gc
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions

FILES = ["test/data/test1.html", "test/data/test3.html"]
REPEAT = 3


def _time(fn, *a) -> float:
    gc.collect()
    best = []
    for _ in range(REPEAT):
        t = time.perf_counter()
        fn(*a)
        best.append(time.perf_counter() - t)
    return min(best) * 1000.0


def bench_file(path: str) -> None:
    html = (ROOT / path).read_text(encoding="utf-8")
    size_kb = len(html.encode()) / 1024
    print(f"\n=== {path} ({size_kb:.0f} KB) ===")

    for force_bs4 in (False, True):
        parser = "BS4" if force_bs4 else "Selectolax"
        opts = MarkdownOptions(force_beautifulsoup=force_bs4, max_length=200_000_000)
        gen = MarkdownGenerator(opts)
        ms = _time(gen.generate_from_html, html)
        out_len = len(gen.generate_from_html(html).fit_markdown)
        print(f"  convert ({parser}): {ms:7.1f} ms   out={out_len:,} chars")

        # raw_markdown lazy
        res = gen.generate_from_html(html)
        t = time.perf_counter()
        raw_len = len(res.raw_markdown)
        raw_ms = (time.perf_counter() - t) * 1000.0
        print(f"  raw_markdown ({parser}): {raw_ms:7.1f} ms   raw={raw_len:,} chars")

        # content-density режим (AUDIT_03 #1 — _find_main_content)
        d_opts = MarkdownOptions(
            force_beautifulsoup=force_bs4, max_length=200_000_000, use_content_density=True
        )
        d_gen = MarkdownGenerator(d_opts)
        d_ms = _time(d_gen.generate_from_html, html)
        print(f"  density ({parser}): {d_ms:7.1f} ms")


if __name__ == "__main__":
    for f in FILES:
        bench_file(f)
