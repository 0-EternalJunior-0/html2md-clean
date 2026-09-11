"""Регресійні бенчмарки на `pytest-benchmark` (AUDIT_04 Б14).

Запуск:
    pytest test/test_benchmarks.py --benchmark-only
    pytest test/test_benchmarks.py --benchmark-only --benchmark-autosave
    pytest --benchmark-compare=0001 --benchmark-compare-fail=mean:10%

Мета — фіксувати `mean`/`stddev` конвертації на еталонних семплах, щоб
CI ловив регресії >10% автоматично. Ідентичне до `perf_check.py`
метричне поле (best-of-3 → mean-of-N), але у форматі, що зберігається у
`.benchmarks/*.json` для diff-порівняння між гілками.

Skipped, якщо `pytest-benchmark` не встановлено (не додаємо у
runtime-залежності — це dev-tool).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pytest.importorskip("pytest_benchmark")

from markdown.generator import MarkdownGenerator  # noqa: E402
from markdown.options import MarkdownOptions  # noqa: E402

DATA = ROOT / "test" / "data"


def _read(name: str) -> str:
    return (DATA / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html_small() -> str:
    return _read("test1.html")


@pytest.fixture(scope="module")
def html_large() -> str:
    return _read("test3.html")


@pytest.mark.parametrize("force_bs4", [False, True], ids=["selectolax", "bs4"])
def test_convert_small(benchmark, html_small: str, force_bs4: bool) -> None:
    opts = MarkdownOptions(force_beautifulsoup=force_bs4, max_length=200_000_000)
    gen = MarkdownGenerator(opts)
    result = benchmark(gen.generate_from_html, html_small)
    assert result.fit_markdown


@pytest.mark.parametrize("force_bs4", [False, True], ids=["selectolax", "bs4"])
def test_convert_large(benchmark, html_large: str, force_bs4: bool) -> None:
    opts = MarkdownOptions(force_beautifulsoup=force_bs4, max_length=200_000_000)
    gen = MarkdownGenerator(opts)
    result = benchmark(gen.generate_from_html, html_large)
    assert result.fit_markdown


def test_raw_markdown_lazy(benchmark, html_large: str) -> None:
    opts = MarkdownOptions(max_length=200_000_000)
    gen = MarkdownGenerator(opts)

    def run() -> int:
        return len(gen.generate_from_html(html_large).raw_markdown)

    length = benchmark(run)
    assert length > 0


def test_density_mode(benchmark, html_large: str) -> None:
    opts = MarkdownOptions(max_length=200_000_000, use_content_density=True)
    gen = MarkdownGenerator(opts)
    result = benchmark(gen.generate_from_html, html_large)
    assert result.fit_markdown
