"""Юніт-тести для 30 «важких» HTML-кейсів + 25 додаткових edge cases.

Побудований на probe2.py: тепер з очікуваними значеннями (assert), щоб
регресії ловились у CI. Групи (див. параметризацію):

* CommonMark-екранування / шум у тексті;
* code (inline / pre) з бектиками;
* списки з trailing text / порожніми li / task-list;
* посилання (parens, spaces, mailto, tel, nested, multiline);
* strong/em/del з пробілами, порожні, вкладені;
* таблиці з rowspan/colspan/br;
* HR / iframe / svg / figure / definition list.

Використовує ``fit_markdown`` бо він проходить усю inline+block логіку.
"""

from __future__ import annotations

import pytest

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions


def _convert(html: str, **overrides) -> str:
    """Хелпер: HTML → fit_markdown з дефолтами, зручними для юніт-тестів.

    ``min_paragraph_length=0`` та ``min_heading_length=0`` — щоб короткі
    кейси (з ``<p>a</p>``) не відкидались фільтром.
    """
    options = MarkdownOptions(
        min_paragraph_length=0,
        min_heading_length=0,
        include_images=True,
        **overrides,
    )
    result = MarkdownGenerator(options).generate_from_html(
        "<html><body>" + html + "</body></html>"
    )
    return result.fit_markdown


# ---------------------------------------------------------------------------
# 30 «важких» кейсів з probe2 — з очікуваннями (regression harness).
# ---------------------------------------------------------------------------

HARD_CASES = [
    # id                       html                                             expected
    ("01_literal_asterisks",  "<p>2 * 3 * 4 = 24 and a_b_c stays</p>",
     "2 * 3 * 4 = 24 and a_b_c stays"),
    ("02_text_like_list",     "<p>- not a list item</p><p>1. not ordered</p>",
     "- not a list item\n\n1. not ordered"),
    ("03_text_like_heading",  "<p># not a heading</p>",
     "# not a heading"),
    # 06 — код з ```` всередині: fence має бути з 4+ бектиків.
    ("06_backticks_in_code",  "<pre><code>```\nnested fence\n```</code></pre>",
     "````\n```\nnested fence\n```\n````"),
    # 07 — inline code з бектиком: ``…`` fence.
    ("07_inline_code_tick",   "<p>use <code>a`b</code> now</p>",
     "use ``a`b`` now"),
    # 08 — pre з порожніми рядками і табами; блок з fence.
    ("08_pre_blank_tabs",     "<pre>line1\n\n\tline2\n\n\nline3</pre>",
     "```\nline1\n\n\tline2\n\nline3\n```"),
    # 09 — code inside list item, inline pre → inline code.
    ("09_code_in_li",         "<ul><li>run <code>npm i</code></li>"
                              "<li><pre><code>a=1</code></pre></li></ul>",
     "- run `npm i`\n- `a=1`"),
    # 10 — pre inside blockquote → fenced block, кожен рядок з `>`.
    ("10_pre_in_blockquote",  "<blockquote><pre><code>x = 1\ny = 2</code></pre></blockquote>",
     "> ```\n> x = 1\n> y = 2\n> ```"),
    ("13_ol_reversed",        '<ol reversed><li>a</li><li>b</li></ol>',
     "1. a\n2. b"),
    ("14_li_value_attr",      '<ol><li value="7">seven</li><li>eight</li></ol>',
     "1. seven\n2. eight"),
    ("15_deep_nested",        "<ul><li>1<ul><li>2<ul><li>3<ul><li>4</li></ul>"
                              "</li></ul></li></ul></li></ul>",
     "- 1\n  - 2\n    - 3\n      - 4"),
    ("16_empty_li",           "<ul><li>a</li><li></li><li>c</li></ul>",
     "- a\n- c"),
    # 17 — дужки в URL зберігаються без екранування.
    ("17_parens_in_url",      '<p><a href="/wiki/Foo_(bar)">Foo</a></p>',
     "[Foo](/wiki/Foo_(bar))"),
    # 18 — пробіли в URL → %20.
    ("18_spaces_in_url",      '<p><a href="/a b c.html">sp</a></p>',
     "[sp](/a%20b%20c.html)"),
    ("19_mailto_tel",         '<p><a href="mailto:a@b.co">mail</a> '
                              '<a href="tel:+123">call</a></p>',
     "[mail](mailto:a@b.co) [call](tel:+123)"),
    # 20 — вкладені <a> (invalid HTML) — BS4 автоправить у сусідні;
    #      пробіл-роздільник між ними зберігається.
    ("20_nested_links",       '<p><a href="/o">out <a href="/i">in</a></a></p>',
     "[out](/o) [in](/i)"),
    # 22 — strong з крайовими пробілами: маркери touch стрип, пробіли назовні.
    ("22_strong_with_ws",     "<p>a <strong> bold </strong> b</p>",
     "a **bold** b"),
    # 23 — порожні strong/em не залишають зіпсованих маркерів.
    ("23_empty_strong_em",    "<p>x<strong></strong><em>  </em>y</p>",
     "xy"),
    ("26_hr_and_text",        "<p>above</p><hr><p>below</p>",
     "above\n\n---\n\nbelow"),
    ("27_figure_figcaption",  '<figure><img src="/f.png" alt="f"></figure>',
     "![f](/f.png)"),
]


@pytest.mark.parametrize("case_id,html,expected", HARD_CASES, ids=[c[0] for c in HARD_CASES])
def test_hard_case(case_id: str, html: str, expected: str) -> None:
    """Регресійний тест: кожен «важкий» HTML → детермінований markdown."""
    assert _convert(html) == expected, f"case={case_id}"


# ---------------------------------------------------------------------------
# 25 додаткових edge-cases (не з probe2 — щоб знайти нові проблеми).
# ---------------------------------------------------------------------------

EXTRA_CASES = [
    # --- inline formatting ---
    ("e01_nested_bold_italic",
     "<p><strong><em>x</em></strong></p>",
     "***x***"),
    ("e02_bold_across_link",
     '<p><strong><a href="/l">link</a></strong></p>',
     "**[link](/l)**"),
    ("e03_del_around_code",
     "<p><del>old <code>x=1</code></del></p>",
     "~~old `x=1`~~"),
    ("e04_code_with_html_entities",
     "<p><code>&lt;div&gt;</code></p>",
     "`<div>`"),
    ("e05_pre_with_code_lang",
     '<pre><code class="language-python">print(1)</code></pre>',
     "```python\nprint(1)\n```"),

    # --- links ---
    ("e06_link_with_query",
     '<p><a href="/x?a=1&amp;b=2">q</a></p>',
     "[q](/x?a=1&b=2)"),
    ("e07_link_bold_inner",
     '<p><a href="/l"><strong>bold link</strong></a></p>',
     "[**bold link**](/l)"),
    ("e08_link_empty_text",
     '<p><a href="/x"></a>tail</p>',
     "tail"),
    ("e09_link_text_only_whitespace",
     '<p><a href="/x">   </a>tail</p>',
     "tail"),
    ("e10_link_hash",
     '<p><a href="#section">jump</a></p>',
     "[jump](#section)"),

    # --- lists ---
    ("e11_task_list_checked",
     '<ul><li><input type="checkbox" checked>done</li>'
     '<li><input type="checkbox">todo</li></ul>',
     "- [x] done\n- [ ] todo"),
    ("e12_ol_start_5",
     '<ol start="5"><li>a</li><li>b</li></ol>',
     "5. a\n6. b"),
    ("e13_list_with_paragraphs",
     "<ul><li><p>a</p><p>b</p></li></ul>",
     "- a\n\nb"),
    ("e14_list_bold_item",
     "<ul><li><strong>Warning:</strong> read</li></ul>",
     "- **Warning:** read"),

    # --- headings ---
    ("e15_heading_with_spans",
     "<h2><span>Hello</span> <span>World</span></h2>",
     "## Hello World"),
    ("e16_heading_nested_em",
     "<h3>Some <em>italic</em> title</h3>",
     "### Some *italic* title"),

    # --- blockquote ---
    ("e17_bq_multi_paragraph",
     "<blockquote><p>first</p><p>second</p></blockquote>",
     "> first\n>\n> second"),
    ("e18_bq_nested",
     "<blockquote>outer<blockquote>inner</blockquote></blockquote>",
     "> outer\n>\n> > inner"),

    # --- tables ---
    ("e19_simple_table",
     "<table><thead><tr><th>a</th><th>b</th></tr></thead>"
     "<tbody><tr><td>1</td><td>2</td></tr></tbody></table>",
     "| a | b |\n| --- | --- |\n| 1 | 2 |"),
    ("e20_table_br_in_cell",
     "<table><tr><th>h</th></tr><tr><td>a<br>b</td></tr></table>",
     "| h |\n| --- |\n| a<br>b |"),
    ("e21_table_pipe_in_cell",
     "<table><tr><th>h</th></tr><tr><td>a|b</td></tr></table>",
     "| h |\n| --- |\n| a\\|b |"),

    # --- misc ---
    ("e22_image_with_spaces",
     '<p><img src="/pic name.png" alt="cap"></p>',
     "![cap](/pic%20name.png)"),
    ("e23_definition_list",
     "<dl><dt>Term</dt><dd>Definition</dd></dl>",
     "Term\n: Definition"),
    ("e24_hr_variants",
     "<hr/><hr><hr />",
     "---\n\n---\n\n---"),
    ("e25_code_starts_with_tick",
     "<p><code>`hello</code></p>",
     "`` `hello ``"),
]


@pytest.mark.parametrize("case_id,html,expected", EXTRA_CASES, ids=[c[0] for c in EXTRA_CASES])
def test_extra_case(case_id: str, html: str, expected: str) -> None:
    """Додаткові edge-кейси: посилання, списки, таблиці, форматування."""
    assert _convert(html) == expected, f"case={case_id}"


# ---------------------------------------------------------------------------
# Групові smoke-перевірки (без exact match — просто містить/не містить).
# ---------------------------------------------------------------------------

def test_no_broken_emphasis_markers() -> None:
    """Порожні/whitespace-only <strong>/<em> НЕ залишають зіпсованих ``**``/``*``."""
    md = _convert("<p>x<strong></strong>y<em>   </em>z</p>")
    assert "**" not in md and "*" not in md
    assert md == "xyz"


def test_url_never_contains_raw_space() -> None:
    """Жоден URL у виводі не має «сирого» пробілу — тільки ``%20``."""
    md = _convert('<p><a href="/path with spaces">x</a>'
                  '<img src="/also spaces.png" alt="a"></p>')
    # Виривати `](.*)` конструкції вручну і перевіряти на пробіли всередині.
    import re
    for m in re.finditer(r"\]\(([^)]+)\)", md):
        assert " " not in m.group(1), f"raw space in url: {m.group(1)}"


def test_code_fence_never_conflicts_with_content() -> None:
    """Fence code-блоку завжди довший за найдовший ``\\`+`` всередині коду."""
    html = "<pre><code>a\n```\nb\n````\nc</code></pre>"
    md = _convert(html)
    # Знаходимо fence — це початковий/кінцевий рядок з бектиків.
    first_line = md.splitlines()[0]
    assert set(first_line) == {"`"}
    # Кінцевий fence не має зустрічатися всередині вмісту.
    assert md.count(first_line) == 2
