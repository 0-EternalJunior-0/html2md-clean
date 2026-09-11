"""AUDIT_04 Б7 — opt-in витяг published/updated date через htmldate."""

import pytest

from markdown import MarkdownGenerator, MarkdownOptions

htmldate = pytest.importorskip("htmldate", reason="htmldate — опційна залежність")


HTML_WITH_DATES = """<html><head><title>Стаття</title>
<meta property="article:published_time" content="2021-03-15T10:00:00Z"/>
<meta property="article:modified_time" content="2023-08-02T09:00:00Z"/>
</head><body><h1>Заголовок</h1><p>Текст статті.</p></body></html>"""

HTML_NO_DATES = "<html><body><h1>H</h1><p>Без дат.</p></body></html>"


def test_dates_off_by_default():
    """Default OFF: поля лишаються None, htmldate навіть не імпортується."""
    result = MarkdownGenerator().generate_from_html(HTML_WITH_DATES)
    assert result.published_date is None
    assert result.updated_date is None


def test_dates_extracted_when_enabled():
    options = MarkdownOptions(extract_dates=True)
    result = MarkdownGenerator(options).generate_from_html(HTML_WITH_DATES)
    assert result.published_date == "2021-03-15"
    assert result.updated_date == "2023-08-02"


def test_dates_do_not_change_markdown():
    """Фіча не має впливати на fit_markdown/text (no output regression)."""
    off = MarkdownGenerator().generate_from_html(HTML_WITH_DATES)
    on = MarkdownGenerator(MarkdownOptions(extract_dates=True)).generate_from_html(
        HTML_WITH_DATES
    )
    assert off.fit_markdown == on.fit_markdown
    assert off.text == on.text


def test_custom_date_format():
    options = MarkdownOptions(extract_dates=True, date_output_format="%d.%m.%Y")
    result = MarkdownGenerator(options).generate_from_html(HTML_WITH_DATES)
    assert result.published_date == "15.03.2021"


def test_no_dates_graceful():
    """Сторінка без дат — None, без винятку."""
    options = MarkdownOptions(extract_dates=True)
    result = MarkdownGenerator(options).generate_from_html(HTML_NO_DATES)
    assert result.published_date is None
    assert result.updated_date is None
    assert result.fit_markdown


def test_missing_htmldate_is_graceful(monkeypatch):
    """Якщо htmldate не встановлено — конвертація не падає."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "htmldate":
            raise ImportError("no htmldate")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    options = MarkdownOptions(extract_dates=True)
    result = MarkdownGenerator(options).generate_from_html(HTML_WITH_DATES)
    assert result.published_date is None
    assert result.fit_markdown
