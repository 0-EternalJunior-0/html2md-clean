"""Регресійні тести на НЕ-табличні HTML-конструкції.

Кожен тест тут закриває реальний баг, знайдений широким скануванням
розмітки (списки, заголовки, blockquote, зображення, legacy-теги):

1. `<h*>` склеював слова (`<span>Hello</span> <span>World</span>` →
   `HelloWorld`), бо `get_text()` у selectolax не вставляє роздільник.
2. Block-діти всередині inline-обходу злипались:
   `<blockquote><p>P1</p><p>P2</p></blockquote>` → `> P1P2`,
   `<li><p>a</p><p>b</p></li>` → `- ab`.
3. `<p><a><img></a></p>` губився цілком — параграф без тексту відкидався.
4. `<ol start="5">` ігнорувався — нумерація завжди починалась з 1.
5. Legacy-обгортки (`<center>`, `<u>`, `<font>`, `<details>`) та голий
   текст прямо в `<body>` мовчки губились.

Усі кейси проганяються обома парсерами (selectolax і BeautifulSoup),
бо саме розбіжність між ними й породила баг №1.
"""

import pytest

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions

PARSERS = [
    pytest.param(False, id="selectolax"),
    pytest.param(True, id="bs4"),
]


def md_of(body_html, force_bs4=False, **opt_kwargs):
    """`<body>`-фрагмент → fit_markdown з поблажливими порогами."""
    defaults = dict(
        min_paragraph_length=0,
        min_heading_length=0,
        include_images=True,
        force_beautifulsoup=force_bs4,
    )
    defaults.update(opt_kwargs)
    opts = MarkdownOptions(**defaults)
    html = f"<html><body>{body_html}</body></html>"
    return MarkdownGenerator(opts).generate_from_html(html).fit_markdown


class TestNonTableConstructs:
    # --- 1. заголовки не склеюють слова ---------------------------------

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_heading_inline_children_not_glued(self, bs4):
        md = md_of("<h2><span>Hello</span> <span>World</span></h2>", bs4)
        assert "## Hello World" in md
        assert "HelloWorld" not in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_heading_keeps_link_and_code(self, bs4):
        md = md_of('<h3>See <a href="/d">docs</a> and <code>run()</code></h3>', bs4)
        assert md.startswith("### ")
        assert "Seedocs" not in md
        for token in ("See", "docs", "run()"):
            assert token in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_heading_is_single_line_with_block_children(self, bs4):
        md = md_of("<h1>Alpha<div>Beta</div></h1>", bs4)
        heading = [ln for ln in md.split("\n") if ln.startswith("# ")]
        assert heading == ["# Alpha Beta"]

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_heading_inner_whitespace_collapsed(self, bs4):
        assert "## Big Title here" in md_of("<h2>   Big    Title   here   </h2>", bs4)

    # --- 2. межі блоків у blockquote / li -------------------------------

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_blockquote_paragraphs_not_concatenated(self, bs4):
        md = md_of("<blockquote><p>P1</p><p>P2</p></blockquote>", bs4)
        assert "P1P2" not in md
        assert "> P1" in md and "> P2" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_nested_blockquote_keeps_boundary(self, bs4):
        md = md_of(
            "<blockquote><p>outer</p><blockquote><p>inner</p></blockquote></blockquote>",
            bs4,
        )
        assert "outerinner" not in md
        assert "outer" in md and "inner" in md
        assert all(ln.startswith(">") for ln in md.split("\n") if ln.strip())

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_blockquote_with_list_items_separated(self, bs4):
        md = md_of("<blockquote><p>Quote:</p><ul><li>a</li><li>b</li></ul></blockquote>", bs4)
        assert "Quote:ab" not in md
        assert "ab" not in md
        assert "a" in md and "b" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_list_item_multiple_paragraphs(self, bs4):
        md = md_of("<ul><li><p>para1</p><p>para2</p></li><li>second</li></ul>", bs4)
        assert "para1para2" not in md
        # Кілька <p> у <li> зберігаються як окремі параграфи (loose list),
        # а не склеюються в один рядок.
        assert "- para1\n\npara2" in md
        assert "- second" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_list_item_block_and_inline_mix(self, bs4):
        md = md_of("<ul><li>text before<div>block inside li</div>text after</li></ul>", bs4)
        assert "beforeblock" not in md
        assert "litext" not in md
        for token in ("text before", "block inside li", "text after"):
            assert token in md

    # --- 3. зображення у параграфі / посиланні --------------------------

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_link_wrapping_image_is_not_dropped(self, bs4):
        md = md_of('<p><a href="/l"><img src="/i.png" alt="pic"></a></p>', bs4)
        assert "/i.png" in md
        assert "![pic](/i.png)" in md
        assert "(/l)" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_image_only_paragraph_survives(self, bs4):
        md = md_of('<p><img src="/solo.png" alt="solo"></p>', bs4)
        assert "![solo](/solo.png)" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_images_disabled_still_keeps_link_text(self, bs4):
        md = md_of('<p><a href="/l">text <img src="/i.png" alt="pic"></a></p>', bs4, include_images=False)
        assert "/i.png" not in md
        assert "text" in md

    # --- 4. ol start ----------------------------------------------------

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_ol_start_attribute_respected(self, bs4):
        md = md_of('<ol start="5"><li>five</li><li>six</li></ol>', bs4)
        assert "5. five" in md
        assert "6. six" in md
        assert "1. five" not in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_ol_invalid_start_falls_back_to_one(self, bs4):
        md = md_of('<ol start="abc"><li>one</li></ol>', bs4)
        assert "1. one" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_ol_numbering_continues_after_nested_list(self, bs4):
        md = md_of("<ol><li>one<ol><li>a</li><li>b</li></ol></li><li>two</li></ol>", bs4)
        assert "1. one" in md
        assert "2. two" in md

    # --- 5. legacy-теги і голий текст -----------------------------------

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_legacy_center_and_u_survive(self, bs4):
        md = md_of("<center>centered text</center><u>underlined</u>", bs4)
        assert "centered text" in md
        assert "underlined" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_bare_body_text_survives(self, bs4):
        assert "loose text at body level" in md_of("loose text at body level", bs4)

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_details_summary_content_survives(self, bs4):
        md = md_of("<details><summary>More info</summary>hidden body</details>", bs4)
        assert "More info" in md
        assert "hidden body" in md

    # --- регресійні гарантії, що нічого не поламалось -------------------

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_code_block_language_and_content_intact(self, bs4):
        md = md_of(
            '<pre><code class="language-python">def f():\n    return 1\n</code></pre>', bs4
        )
        assert "```python" in md
        assert "def f():" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_definition_list_multiple_dd(self, bs4):
        md = md_of("<dl><dt>Term</dt><dd>def1</dd><dd>def2</dd></dl>", bs4)
        assert "Term" in md
        assert ": def1" in md and ": def2" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_nested_inline_formatting_preserved(self, bs4):
        md = md_of('<p><strong>bold <a href="/l">link</a> more</strong></p>', bs4)
        assert "**bold [link](/l) more**" in md



class TestDeepBlockquote:
    """Складні випадки справжньої багаторівневої вкладеності ``<blockquote>``.

    Перевіряє, що глибина вкладення НЕ схлопується в один рівень, а
    зберігається за CommonMark (``> ``, ``> > ``, ``> > > ``…), і що
    результат ідентичний для обох парсерів (selectolax та BeautifulSoup).
    Кожен непорожній рядок цитати мусить починатися з ``>``.
    """

    @staticmethod
    def _quote_lines(md):
        return [ln for ln in md.split("\n") if ln.strip()]

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_three_levels_increasing_prefix(self, bs4):
        html = (
            "<blockquote><p>L1</p>"
            "<blockquote><p>L2</p>"
            "<blockquote><p>L3</p></blockquote>"
            "</blockquote></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> L1" in md
        assert "> > L2" in md
        assert "> > > L3" in md
        # Жодного схлопування рівнів у щось на кшталт `> L2` для L3.
        assert "> L3" not in md.replace("> > > L3", "")

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_four_levels_deep(self, bs4):
        html = "<blockquote>" * 4 + "<p>deep</p>" + "</blockquote>" * 4
        md = md_of(html, bs4)
        assert "> > > > deep" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_every_nonblank_line_is_quoted(self, bs4):
        html = (
            "<blockquote><p>outer</p>"
            "<blockquote><p>mid</p>"
            "<blockquote><p>inner</p></blockquote></blockquote></blockquote>"
        )
        md = md_of(html, bs4)
        assert all(ln.startswith(">") for ln in self._quote_lines(md))

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_sibling_after_nested_drops_back_one_level(self, bs4):
        # Параграф-сусід ПІСЛЯ вкладеної цитати повертається на рівень 1.
        html = (
            "<blockquote><p>A</p>"
            "<blockquote><p>B</p></blockquote>"
            "<p>C</p></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> A" in md
        assert "> > B" in md
        assert "> C" in md
        # C не повинен лишитися на другому рівні.
        lines = md.split("\n")
        assert "> C" in lines and "> > C" not in lines

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_bare_text_without_p_wrappers(self, bs4):
        html = "<blockquote>outer text<blockquote>inner text</blockquote></blockquote>"
        md = md_of(html, bs4)
        assert "outerinner" not in md
        assert "> outer text" in md
        assert "> > inner text" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_nested_list_is_quoted_at_correct_depth(self, bs4):
        html = (
            "<blockquote><p>Q</p>"
            "<blockquote><ul><li>x</li><li>y</li></ul></blockquote></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> Q" in md
        assert "> > - x" in md
        assert "> > - y" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_nested_code_block_quoted(self, bs4):
        html = (
            "<blockquote><blockquote>"
            "<pre><code>print(1)</code></pre>"
            "</blockquote></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> > ```" in md
        assert "> > print(1)" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_nested_heading_quoted(self, bs4):
        html = (
            "<blockquote><blockquote>"
            "<h2>Title</h2><p>body</p>"
            "</blockquote></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> > ## Title" in md
        assert "> > body" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_inline_formatting_preserved_across_levels(self, bs4):
        html = (
            "<blockquote><p>a <strong>bold</strong></p>"
            "<blockquote><p><em>it</em> b</p></blockquote></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> a **bold**" in md
        assert "> > *it* b" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_hard_break_preserved_inside_nested(self, bs4):
        html = "<blockquote><blockquote><p>line1<br>line2</p></blockquote></blockquote>"
        md = md_of(html, bs4)
        assert "> > line1  \n> > line2" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_nested_first_then_sibling(self, bs4):
        html = (
            "<blockquote><blockquote><p>inner</p></blockquote>"
            "<p>after</p></blockquote>"
        )
        md = md_of(html, bs4)
        assert "> > inner" in md
        assert "> after" in md

    @pytest.mark.parametrize("bs4", PARSERS)
    def test_parser_output_identical(self, bs4):
        # Той самий вхід має давати ідентичний markdown для обох парсерів.
        html = (
            "<blockquote><p>L1</p>"
            "<blockquote><p>L2</p>"
            "<blockquote><ul><li>a</li></ul></blockquote>"
            "</blockquote></blockquote>"
        )
        assert md_of(html, False) == md_of(html, True)
