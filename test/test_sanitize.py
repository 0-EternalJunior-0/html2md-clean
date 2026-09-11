"""AUDIT_04 Б15 — opt-in санітизація HTML через nh3 (Rust/ammonia)."""

import pytest

from markdown import MarkdownGenerator, MarkdownOptions

nh3 = pytest.importorskip("nh3", reason="nh3 — опційна залежність")


XSS_HTML = (
    '<div><p>Safe text</p>'
    '<script>alert(1)</script>'
    '<a href="javascript:alert(3)">click</a> '
    '<a href="https://ok.com">ok</a>'
    '<img src="x" onerror="alert(2)" alt="pic"></div>'
)


def _md(**opts):
    options = MarkdownOptions(include_images=True, **opts)
    return MarkdownGenerator(options).generate_from_html(XSS_HTML).fit_markdown


def test_sanitize_off_by_default():
    """Default OFF: javascript:-URL доходить до markdown як є."""
    assert "javascript:alert(3)" in _md()


def test_sanitize_strips_javascript_url():
    """З sanitize_html=True javascript:-URL зникає, текст лишається."""
    out = _md(sanitize_html=True)
    assert "javascript:" not in out
    assert "click" in out


def test_sanitize_keeps_legitimate_links():
    out = _md(sanitize_html=True)
    assert "[ok](https://ok.com)" in out


def test_sanitize_removes_script_payload():
    out = _md(sanitize_html=True)
    assert "alert(1)" not in out
    assert "Safe text" in out


def test_sanitize_removes_event_handlers():
    """on*-обробники вирізаються ще на рівні nh3."""
    assert "onerror" not in nh3.clean(XSS_HTML)


def test_sanitize_empty_result_is_graceful():
    """HTML, що після санітизації порожній, не спричиняє помилку."""
    options = MarkdownOptions(sanitize_html=True)
    result = MarkdownGenerator(options).generate_from_html("<script>alert(1)</script>")
    assert result.fit_markdown == ""


def test_missing_nh3_is_graceful(monkeypatch):
    """Якщо nh3 не встановлено — конвертація йде без санітизації, без падіння."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "nh3":
            raise ImportError("no nh3")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    options = MarkdownOptions(include_images=True, sanitize_html=True)
    result = MarkdownGenerator(options).generate_from_html(XSS_HTML)
    assert "Safe text" in result.fit_markdown
