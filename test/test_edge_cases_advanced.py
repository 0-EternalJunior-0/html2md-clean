"""Розвідка №3: складніші, «дуже нестандартні» HTML-кейси з очікуваннями.

Продовження ``test_hard_cases.py``. Тут — глибші комбінації, на яких падають
навіть непогані конвертери:

* картинки-посилання (``[![alt](img)](href)``), autolink;
* блокові конструкції всередині ``<blockquote>`` (заголовки, hr, код, списки);
* нумерація вкладених ``<ol>`` та bullet-cycling;
* inline у клітинках таблиць (лінки, ``|`` у URL, ``<br>``, rowspan-block);
* typography-сутності, sub/sup/mark, code-fence з мовою;
* злиття/втрата тексту на межах inline↔block.

Усі очікування — детерміновані ``fit_markdown`` (regression harness).
"""

from __future__ import annotations

import pytest

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions


def _convert(html: str, **overrides) -> str:
    options = MarkdownOptions(
        min_paragraph_length=0,
        min_heading_length=0,
        include_images=True,
        **overrides,
    )
    return MarkdownGenerator(options).generate_from_html(
        "<html><body>" + html + "</body></html>"
    ).fit_markdown


ADVANCED_CASES = [
    # --- images & links ---
    ("a01_image_link",
     '<p><a href="/l"><img src="/i.png" alt="x"></a></p>',
     "[![x](/i.png)](/l)"),
    ("a02_autolink_text_equals_url",
     '<p><a href="http://x.com">http://x.com</a></p>',
     "[http://x.com](http://x.com)"),
    ("a03_link_space_around_inner",
     '<p>go <a href="/l"> here </a> now</p>',
     "go [here](/l) now"),
    ("a04_image_only_paragraph_kept",
     '<p><img src="/only.png" alt="solo"></p>',
     "![solo](/only.png)"),
    ("a05_link_wrapping_emphasis_and_code",
     '<p><a href="/l">see <em>this</em> <code>x</code></a></p>',
     "[see *this* `x`](/l)"),

    # --- blockquote: block-level children preserved ---
    ("a06_bq_heading_and_body",
     "<blockquote><h2>Title</h2><p>body</p></blockquote>",
     "> ## Title\n>\n> body"),
    ("a07_bq_with_hr",
     "<blockquote><p>note</p><hr><p>end</p></blockquote>",
     "> note\n>\n> ---\n>\n> end"),
    ("a08_bq_with_code_lang",
     '<blockquote><pre><code class="language-py">x=1</code></pre></blockquote>',
     "> ```py\n> x=1\n> ```"),
    ("a09_bq_with_list",
     "<blockquote><p>items:</p><ul><li>a</li><li>b</li></ul></blockquote>",
     "> items:\n>\n> - a\n> - b"),
    ("a10_bq_triple_nested_levels",
     "<blockquote>a<blockquote>b<blockquote>c</blockquote></blockquote></blockquote>",
     "> a\n>\n> > b\n> >\n> > > c"),

    # --- lists: numbering / cycling / nesting ---
    ("a11_nested_ol_numbering",
     "<ol><li>a<ol><li>x</li><li>y</li></ol></li><li>b</li></ol>",
     "1. a\n  1. x\n  2. y\n2. b"),
    ("a12_triple_nested_bullets",
     "<ul><li>1<ul><li>2<ul><li>3</li></ul></li></ul></li></ul>",
     "- 1\n  - 2\n    - 3"),
    ("a13_ol_in_ul_mixed",
     "<ul><li>top<ol><li>one</li><li>two</li></ol></li></ul>",
     "- top\n  1. one\n  2. two"),
    ("a14_li_leading_nested_list",
     "<ul><li><ul><li>nested</li></ul>after</li></ul>",
     "- after\n  - nested"),
    ("a15_li_paragraph_then_list",
     "<ul><li><p>intro</p><ul><li>x</li></ul></li></ul>",
     "- intro\n  - x"),

    # --- tables: inline content in cells ---
    ("a16_cell_link",
     '<table><tr><th>h</th></tr><tr><td><a href="/u">go</a></td></tr></table>',
     "| h |\n| --- |\n| [go](/u) |"),
    ("a17_cell_pipe_in_link_url",
     '<table><tr><th>h</th></tr><tr><td><a href="/a|b">l</a></td></tr></table>',
     "| h |\n| --- |\n| [l](/a\\|b) |"),
    ("a18_cell_bold_and_br",
     "<table><tr><th>h</th></tr><tr><td><strong>A</strong><br>B</td></tr></table>",
     "| h |\n| --- |\n| **A**<br>B |"),
    ("a19_cell_list_becomes_br",
     "<table><tr><th>h</th></tr><tr><td><ul><li>a</li><li>b</li></ul></td></tr></table>",
     "| h |\n| --- |\n| a<br>b |"),

    # --- headings & typography ---
    ("a20_heading_with_br_single_line",
     "<h2>line1<br>line2</h2>",
     "## line1 line2"),
    ("a21_heading_trailing_colon_and_code",
     "<h3>Setup <code>env</code>:</h3>",
     "### Setup `env`:"),
    ("a22_entities_typography",
     "<p>caf&eacute; &mdash; &ldquo;quote&rdquo; &hellip;</p>",
     "café — “quote” …"),
    ("a23_sup_sub_preserved_as_text",
     "<p>x<sup>2</sup>+H<sub>2</sub>O</p>",
     "x2+H2O"),
    ("a24_mark_kbd_abbr_text_kept",
     '<p><mark>hot</mark> <kbd>Esc</kbd> <abbr title="t">WWW</abbr></p>',
     "hot Esc WWW"),

    # --- code fences ---
    ("a25_code_fence_five_backticks",
     "<pre><code>a\n```\nb\n````\nc</code></pre>",
     "`````\na\n```\nb\n````\nc\n`````"),
    ("a26_pre_without_code_tag",
     "<pre>plain\n  indented\nend</pre>",
     "```\nplain\n  indented\nend\n```"),
    ("a27_code_block_trailing_blank_lines_trimmed",
     "<pre><code>line\n\n\n</code></pre>",
     "```\nline\n```"),

    # --- inline emphasis edge ---
    ("a28_strong_touching_punctuation",
     "<p>see <strong>bold</strong>, ok</p>",
     "see **bold**, ok"),
    ("a29_del_with_leading_space",
     "<p>a<del> gone </del>b</p>",
     "a ~~gone~~ b"),
    ("a30_bold_italic_del_combo",
     "<p><strong>b <em>i <del>d</del></em></strong></p>",
     "**b *i ~~d~~***"),
]


@pytest.mark.parametrize(
    "case_id,html,expected", ADVANCED_CASES, ids=[c[0] for c in ADVANCED_CASES]
)
def test_advanced_case(case_id: str, html: str, expected: str) -> None:
    """Складні комбінації: картинки-лінки, blockquote-блоки, таблиці, typography."""
    assert _convert(html) == expected, f"case={case_id}"


# ---------------------------------------------------------------------------
# Інваріантні (property-style) перевірки — без exact match.
# ---------------------------------------------------------------------------

def test_blockquote_never_loses_heading_marker() -> None:
    """Заголовок усередині blockquote зберігає ``#``-маркер."""
    md = _convert("<blockquote><h1>H</h1><h3>h3</h3></blockquote>")
    assert "> # H" in md
    assert "> ### h3" in md


def test_image_link_order_is_alt_src_href() -> None:
    """``<a><img></a>`` → ``[![alt](src)](href)`` (порядок не переплутано)."""
    md = _convert('<a href="H"><img src="S" alt="A"></a>')
    assert md == "[![A](S)](H)"


def test_nested_ordered_lists_restart_numbering() -> None:
    """Вкладений ``<ol>`` нумерується з 1, зовнішній продовжує свою нумерацію."""
    md = _convert(
        "<ol><li>a<ol><li>x</li><li>y</li></ol></li><li>b</li></ol>"
    )
    lines = md.split("\n")
    assert lines[0] == "1. a"
    assert lines[-1] == "2. b"
    assert "  1. x" in md and "  2. y" in md


def test_table_cells_never_emit_raw_pipe() -> None:
    """У клітинках таблиці немає неекранованого ``|`` (окрім роздільників)."""
    import re
    md = _convert(
        '<table><tr><th>h</th></tr>'
        '<tr><td>a|b</td></tr><tr><td><a href="/x|y">l</a></td></tr></table>'
    )
    for line in md.split("\n"):
        if not line.startswith("|"):
            continue
        inner = line.strip().strip("|")
        cells = re.split(r"(?<!\\)\|", inner)
        # Кожна клітинка не містить «сирого» pipe.
        for cell in cells:
            assert "|" not in cell.replace("\\|", ""), f"raw pipe у клітинці: {cell!r}"


def test_blockquote_code_block_is_fenced_not_inline() -> None:
    """``<pre>`` у blockquote → fenced-блок (``> ``` ``), а не однорядковий inline."""
    md = _convert("<blockquote><pre><code>x = 1\ny = 2</code></pre></blockquote>")
    assert md == "> ```\n> x = 1\n> y = 2\n> ```"


def test_bullet_cycling_by_depth() -> None:
    """``options.bullets='-*+'`` → маркер циклиться за глибиною вкладеності."""
    md = _convert(
        "<ul><li>1<ul><li>2<ul><li>3</li></ul></li></ul></li></ul>",
        bullets="-*+",
    )
    assert md == "- 1\n  * 2\n    + 3"


def test_deep_blockquote_adds_level_per_nesting() -> None:
    """Кожен вкладений ``<blockquote>`` додає рівень ``> `` (справжня багаторівнева цитата)."""
    md = _convert("<blockquote>a<blockquote>b<blockquote>c</blockquote></blockquote></blockquote>")
    assert md == "> a\n>\n> > b\n> >\n> > > c"
    # Найглибший рядок має рівно 3 рівні цитування.
    assert "> > > c" in md
    # Кожен непорожній рядок починається з '>'.
    assert all(ln.startswith(">") for ln in md.split("\n") if ln.strip())


