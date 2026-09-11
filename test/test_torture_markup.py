"""Stress / «torture» тести на жахливу, нестандартну та legacy-розмітку.

Мета — впіймати регресії, за яких у продакшені дані з HTML **губляться**,
**склеюються** або таблиця **зсувається по колонках**. Кожен кейс імітує
типовий (потворний) вивід реального стеку: WordPress/PHP, React SSR, Angular,
Django, Java/JSP, HTML4-legacy, XHTML, а також «биту» розмітку з незакритими
тегами.

Політика перевірок:
- увесь видимий текст має дійти до Markdown (без мовчазної втрати);
- слова, розділені пробілом у HTML, не мають склеюватись;
- усі рядки однієї таблиці мають однакову кількість `|`-колонок;
- `|` і переноси в клітинках екрануються (`\\|`, `<br>`);
- битий HTML не валить конвертер.
"""

import re

import pytest

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions


def md_of(html, **opt_kwargs):
    """HTML → fit_markdown з поблажливими порогами (короткий контент не ріжеться)."""
    defaults = dict(min_paragraph_length=0, min_heading_length=0)
    defaults.update(opt_kwargs)
    opts = MarkdownOptions(**defaults)
    return MarkdownGenerator(opts).generate_from_html(html).fit_markdown


def table_rows(md):
    """Повертає рядки-таблиці (ті, що починаються з `|`) зі згенерованого md."""
    return [ln for ln in md.split("\n") if ln.strip().startswith("|")]


def assert_table_columns_consistent(md):
    """Кожна група таблиці має стабільну кількість колонок (однаковий count `|`).

    Розбиваємо на суміжні блоки `|`-рядків (кілька таблиць в одному документі)
    і в межах кожного блоку вимагаємо однакову кількість роздільників.
    """
    block = []
    blocks = []
    for ln in md.split("\n"):
        if ln.strip().startswith("|"):
            block.append(ln)
        elif block:
            blocks.append(block)
            block = []
    if block:
        blocks.append(block)

    for blk in blocks:
        # Рахуємо лише НЕекрановані `|` (роздільники колонок), ігноруючи `\|`.
        counts = {len(re.findall(r"(?<!\\)\|", ln)) for ln in blk}
        assert len(counts) == 1, f"нестабільна ширина таблиці: {counts}\n" + "\n".join(blk)


# ═══════════════════════════════════════════════════════════════════════════
#  Фреймворк-специфічний потворний вивід
# ═══════════════════════════════════════════════════════════════════════════

class TestFrameworkOutputs:

    def test_wordpress_nested_divs_and_shortcode(self):
        html = """<html><body>
        <div class="entry-content"><div class="wp-block-group"><div class="inner">
        <p style="text-align:left">Перший <strong>жирний</strong> абзац з <a href="/p">лінком</a>.</p>
        <p>Другий абзац.&nbsp;Ще речення.</p>
        </div></div></div></body></html>"""
        md = md_of(html)
        assert "**жирний**" in md
        assert "[лінком](/p)" in md
        assert "Другий абзац. Ще речення." in md  # &nbsp; → звичайний пробіл

    def test_react_ssr_text_split_across_spans_no_word_glue(self):
        # Текст, порізаний на десятки <span>: пробіли з HTML мають зберегтись.
        html = """<html><body><div data-reactroot="">
        <p><span>Ціна</span><span>: </span><span>1</span><span>299</span><span> грн</span></p>
        <p><span>Слово</span> <span>з</span> <span>пробілами</span></p>
        </div></body></html>"""
        md = md_of(html)
        assert "Ціна: 1299 грн" in md          # без пробілу в джерелі → не додаємо
        assert "Слово з пробілами" in md        # пробіли в джерелі → зберігаємо

    def test_angular_custom_elements_and_ng_attrs(self):
        html = """<html><body><app-root _nghost-abc="">
        <app-content><article><h2 _ngcontent-abc="">Новина</h2>
        <p _ngcontent-abc="">Тіло <em>новини</em> тут.</p></article></app-content>
        </app-root></body></html>"""
        md = md_of(html)
        assert "## Новина" in md
        assert "Тіло *новини* тут." in md

    def test_django_whitespace_heavy_nested_lists(self):
        html = """<html><body><div class="content">
            <ul>
                <li>Головне
                    <ul><li>Підпункт 1</li><li>Підпункт 2</li></ul>
                </li>
                <li>Ще одне</li>
            </ul>
            <ol><li>Крок 1</li><li>Крок 2</li></ol>
        </div></body></html>"""
        md = md_of(html)
        for token in ("Головне", "Підпункт 1", "Підпункт 2", "Ще одне", "Крок 1", "Крок 2"):
            assert token in md, f"втрачено: {token}"
        assert "  - Підпункт 1" in md  # вкладеність збережена відступом

    def test_java_jsp_code_block_and_result_table(self):
        html = """<html><body>
        <pre><code class="language-java">public class A { int x = 1|2; }</code></pre>
        <table><thead><tr><th>id</th><th>name</th></tr></thead>
        <tbody><tr><td>1</td><td>Alice</td></tr><tr><td>2</td><td>Bob</td></tr></tbody></table>
        </body></html>"""
        md = md_of(html)
        assert "```java" in md
        assert "int x = 1|2;" in md            # усередині коду | НЕ екранується
        assert "| 1 | Alice |" in md
        assert "| 2 | Bob |" in md


# ═══════════════════════════════════════════════════════════════════════════
#  Версії HTML та «підводні» фішки форматування
# ═══════════════════════════════════════════════════════════════════════════

class TestHtmlVersionQuirks:

    def test_html4_legacy_layout_table(self):
        html = """<html><body>
        <table border="1"><tr><td><b>Ім'я</b></td><td>Іван</td></tr>
        <tr><td><b>Вік</b></td><td>30</td></tr></table></body></html>"""
        md = md_of(html)
        assert "| **Ім'я** | Іван |" in md
        assert "| **Вік** | 30 |" in md
        assert_table_columns_consistent(md)

    def test_xhtml_self_closing_and_entities(self):
        html = """<html><body>
        <p>Рядок1<br/>Рядок2<br/>Рядок3</p>
        <p>AT&amp;T &lt;тег&gt; &#8220;лапки&#8221; &mdash; тире &copy;2024</p>
        </body></html>"""
        md = md_of(html)
        assert "Рядок1" in md and "Рядок2" in md and "Рядок3" in md
        # entities декодуються, а не лишаються сирими
        assert "AT&T" in md
        assert "&amp;" not in md and "&lt;" not in md
        assert "<тег>" in md
        assert "©2024" in md

    def test_unclosed_tags_do_not_crash_or_lose_list_items(self):
        # Незакриті <p> та <li> — браузер/парсер закриває сам.
        html = """<html><body>
        <p>Абзац один
        <p>Абзац два
        <ul><li>Пункт A<li>Пункт B<li>Пункт C</ul></body></html>"""
        md = md_of(html)
        assert "Абзац один" in md and "Абзац два" in md
        for token in ("Пункт A", "Пункт B", "Пункт C"):
            assert token in md

    def test_deeply_nested_blocks_preserve_content(self):
        html = """<html><body>
        <section><div><article><div><blockquote>
        <p>Глибоко вкладена цитата з <code>inline code</code>.</p>
        </blockquote></div></article></div></section></body></html>"""
        md = md_of(html)
        assert "Глибоко вкладена цитата" in md
        assert "`inline code`" in md
        assert "> Глибоко" in md  # blockquote-маркер збережений

    def test_figure_with_caption_keeps_image_and_caption(self):
        html = """<html><body>
        <figure><img src="/chart.png" alt="Графік продажів">
        <figcaption>Рис. 1. Продажі за рік</figcaption></figure>
        <p>Текст після.</p></body></html>"""
        md = md_of(html, include_images=True)
        assert "![Графік продажів](/chart.png)" in md
        assert "Рис. 1. Продажі за рік" in md
        assert "Текст після." in md

    def test_adjacent_inline_and_nested_emphasis(self):
        html = """<html><body>
        <p><strong>жирний <em>та курсив <code>та код</code></em></strong> кінець.</p>
        </body></html>"""
        md = md_of(html)
        assert "**жирний *та курсив `та код`*** кінець." in md


# ═══════════════════════════════════════════════════════════════════════════
#  Таблиці: геометрія, tfoot, вкладеність, екранування (втрата даних)
# ═══════════════════════════════════════════════════════════════════════════

class TestTableIntegrity:

    def test_tfoot_rows_are_not_lost(self):
        html = """<html><body><table>
        <thead><tr><th>Товар</th><th>Сума</th></tr></thead>
        <tbody><tr><td>Кава</td><td>10</td></tr><tr><td>Чай</td><td>12</td></tr></tbody>
        <tfoot><tr><td>Разом</td><td>22</td></tr></tfoot>
        </table></body></html>"""
        md = md_of(html)
        assert "| Разом | 22 |" in md, "tfoot-рядок втрачено (пошкодження даних)"
        assert_table_columns_consistent(md)

    def test_multiple_tbody_sections_all_kept(self):
        html = """<html><body><table>
        <tbody><tr><td>a</td><td>1</td></tr></tbody>
        <tbody><tr><td>b</td><td>2</td></tr></tbody>
        </table></body></html>"""
        md = md_of(html)
        assert "| a | 1 |" in md and "| b | 2 |" in md
        assert_table_columns_consistent(md)

    def test_full_complex_table_geometry_stable(self):
        html = """<html><body><table>
        <caption>Звіт</caption>
        <thead><tr><th rowspan="2">Місяць</th><th colspan="2">Регіон</th></tr>
        <tr><th>Захід</th><th>Схід</th></tr></thead>
        <tbody>
        <tr><td>Січень</td><td>10</td><td>20</td></tr>
        <tr><td rowspan="2">Лют-Бер</td><td>5</td><td>6</td></tr>
        <tr><td>7</td><td>8</td></tr>
        </tbody>
        <tfoot><tr><td>Разом</td><td>22</td><td>34</td></tr></tfoot>
        </table></body></html>"""
        md = md_of(html)
        assert "| Місяць | Регіон Захід | Регіон Схід |" in md
        assert "| Лют-Бер | 5 | 6 |" in md
        assert "| Лют-Бер | 7 | 8 |" in md     # rowspan протягнутий
        assert "| Разом | 22 | 34 |" in md      # tfoot присутній
        assert_table_columns_consistent(md)

    def test_nested_table_stays_inside_one_cell(self):
        html = """<html><body><table>
        <tr><td>Деталі</td><td><table><tr><td>a</td><td>b</td></tr>
        <tr><td>c</td><td>d</td></tr></table></td></tr></table></body></html>"""
        md = md_of(html)
        assert "a / b<br>c / d" in md
        # Вкладена таблиця не додала власних |-рядків у зовнішню геометрію.
        assert_table_columns_consistent(md)

    def test_pipe_and_newline_escaped_in_cells(self):
        html = """<html><body><table><tr><th>Код</th><th>Опис</th></tr>
        <tr><td>a|b</td><td>рядок1<br>рядок2</td></tr>
        <tr><td>c</td><td>вміст з | трубою</td></tr></table></body></html>"""
        md = md_of(html)
        assert r"| a\|b | рядок1<br>рядок2 |" in md
        assert r"вміст з \| трубою" in md
        assert_table_columns_consistent(md)

    def test_ragged_rows_padded_to_max_width(self):
        html = """<html><body><table>
        <thead><tr><th>A</th><th>B</th><th>C</th></tr></thead>
        <tbody><tr><td>1</td><td>2</td><td>3</td></tr>
        <tr><td>4</td><td>5</td></tr></tbody></table></body></html>"""
        md = md_of(html)
        assert_table_columns_consistent(md)  # короткий рядок добито до 3 колонок


# ═══════════════════════════════════════════════════════════════════════════
#  Robustness: битий / екзотичний HTML не валить конвертер
# ═══════════════════════════════════════════════════════════════════════════

class TestRobustness:

    @pytest.mark.parametrize("html", [
        "<table><tr><td rowspan='9999'>x</td><td>a</td></tr><tr><td>b</td></tr></table>",
        "<table><tr><td colspan='0'>z</td></tr></table>",
        "<table><tr><td rowspan='abc' colspan='-5'>q</td><td>w</td></tr></table>",
        "<div><p>текст<div>вкладений блок у параграфі</div></p></div>",
        "<ul><li><table><tr><td>таб у списку</td></tr></table></li></ul>",
        "<table></table>",
        "<table><tr></tr></table>",
        "<p>&#65533; &#x1F600; емодзі та реплейсмент</p>",
        "<td>сирота без таблиці</td>",
        "<b><b><b>тричі жирний</b></b></b>",
    ])
    def test_malformed_html_does_not_raise(self, html):
        md = md_of("<html><body>" + html + "</body></html>")
        assert isinstance(md, str)
        # Будь-яка згенерована таблиця має стабільну ширину.
        assert_table_columns_consistent(md)

    def test_empty_and_whitespace_only(self):
        assert md_of("<html><body></body></html>") == ""
        assert md_of("<html><body>   \n\t  </body></html>").strip() == ""

    def test_massive_table_performance_smoke(self):
        # 200×5 таблиця з rowspan у першій колонці — не зависає й геометрія стабільна.
        rows = ["<tr><td rowspan='2'>R%d</td><td>a</td><td>b</td><td>c</td><td>d</td></tr>"
                "<tr><td>a</td><td>b</td><td>c</td><td>d</td></tr>" % i for i in range(100)]
        html = "<html><body><table>" + "".join(rows) + "</table></body></html>"
        md = md_of(html)
        assert_table_columns_consistent(md)
        assert md.count("\n") >= 200


# ═══════════════════════════════════════════════════════════════════════════
#  Екзотика: потрійно вкладені таблиці, block-контент у клітинці,
#  colgroup/caption/scope, misnested inline + рідкісний Unicode
# ═══════════════════════════════════════════════════════════════════════════

class TestExoticEdgeCases:

    def test_triple_nested_tables_no_row_duplication(self):
        # Таблиця в таблиці в таблиці всередині клітинки з rowspan.
        # Рядки найглибшої таблиці НЕ мають дублюватись у серіалізації.
        html = """<html><body><table>
        <tr><td rowspan="2">
            <table><tr><td>L1a</td>
            <td><table><tr><td>L2x</td><td>L2y</td></tr></table></td></tr></table>
        </td><td>Side</td></tr>
        <tr><td>Bot</td></tr></table></body></html>"""
        md = md_of(html)
        assert "| L1a / L2x / L2y | Side |" in md
        assert "| L1a / L2x / L2y | Bot |" in md
        # "L2x / L2y" зустрічається рівно по разу в кожному рядку (без дублю).
        assert "L2x / L2y<br>" not in md
        assert_table_columns_consistent(md)

    def test_block_content_cell_multi_paragraph_and_list_over_rowspan(self):
        # Клітинка з кількома <p> та вкладеним <ul>, протягнута по rowspan.
        html = """<html><body><table>
        <tr><th>K</th><th>V</th></tr>
        <tr><td rowspan="2"><p>Para1</p><p>Para2</p><ul><li>i1</li><li>i2</li></ul></td><td>A</td></tr>
        <tr><td>B</td></tr></table></body></html>"""
        md = md_of(html)
        cell = "Para1<br>Para2<br>i1<br>i2"
        assert f"| {cell} | A |" in md
        assert f"| {cell} | B |" in md   # той самий вміст протягнуто вниз
        assert_table_columns_consistent(md)

    def test_colgroup_caption_scope_and_wider_data_row(self):
        # colgroup/col/caption/th-scope ігноруються без падіння; рядок даних
        # ШИРШИЙ за заголовок → заголовок добивається, дані НЕ губляться.
        html = """<html><body><table>
        <caption>Звіт</caption>
        <colgroup><col><col></colgroup>
        <thead><tr><th scope="col">H1</th><th scope="col">H2</th></tr></thead>
        <tbody><tr><td>a</td><td>b</td><td>EXTRA</td></tr></tbody></table></body></html>"""
        md = md_of(html)
        assert "EXTRA" in md, "надлишкова клітинка втрачена"
        assert "| a | b | EXTRA |" in md
        assert_table_columns_consistent(md)  # header добито до 3 колонок

    def test_misnested_inline_and_rare_unicode_preserve_text(self):
        # Перехресні (некоректно вкладені) inline-теги + zero-width, soft hyphen,
        # emoji (surrogate pair) — увесь ВИДИМИЙ текст має дійти без втрати.
        html = ("<html><body>"
                "<p><b>bold<i>both</b>italic</i> end</p>"
                "<p>zero\u200bwidth soft\u00adhyphen \U0001F600 emoji</p>"
                "</body></html>")
        md = md_of(html)
        for token in ("bold", "both", "italic", "end", "emoji"):
            assert token in md, f"втрачено токен: {token}"
        assert "\U0001F600" in md          # emoji (surrogate pair) збережено
        assert "zero\u200bwidth" in md      # zero-width joiner не з'їв текст
