"""Розвідка №2: 30 «важких» HTML-кейсів, на яких звичайні конвертери падають.

Не тест — дослідницький скрипт. Друкує repr(markdown) для кожного кейсу,
щоб очима знайти втрату/склеювання/зіпсовану розмітку.
"""

import os

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions

BS4 = bool(os.environ.get("BS4"))


def c(h, **kw):
    o = MarkdownOptions(
        min_paragraph_length=0,
        min_heading_length=0,
        include_images=True,
        force_beautifulsoup=BS4,
        **kw,
    )
    return MarkdownGenerator(o).generate_from_html("<html><body>" + h + "</body></html>").fit_markdown


CASES = [
    # --- екранування CommonMark: текст, що виглядає як розмітка ---
    ("01 literal asterisks in text", "<p>2 * 3 * 4 = 24 and a_b_c stays</p>"),
    ("02 text starting like a list", "<p>- not a list item</p><p>1. not ordered</p>"),
    ("03 text starting like heading", "<p># not a heading</p>"),
    ("04 markdown link chars in text", "<p>see [1] (ref) and ![no](img)</p>"),
    ("05 pipe and backslash in text", "<p>a | b \\ c</p>"),
    # --- code / pre ---
    ("06 code containing triple backticks", "<pre><code>```\nnested fence\n```</code></pre>"),
    ("07 inline code with backtick", "<p>use <code>a`b</code> now</p>"),
    ("08 pre with blank lines + tabs", "<pre>line1\n\n\tline2\n\n\nline3</pre>"),
    ("09 code inside list item", "<ul><li>run <code>npm i</code></li><li><pre><code>a=1</code></pre></li></ul>"),
    ("10 pre inside blockquote", "<blockquote><pre><code>x = 1\ny = 2</code></pre></blockquote>"),
    # --- списки, важкі варіанти ---
    ("11 li with nested ol and trailing text", "<ol><li>a<ul><li>b</li></ul>tail</li></ol>"),
    ("12 ul directly inside ul (no li)", "<ul><ul><li>orphan</li></ul></ul>"),
    ("13 ol reversed", '<ol reversed><li>a</li><li>b</li></ol>'),
    ("14 li value attr", '<ol><li value="7">seven</li><li>eight</li></ol>'),
    ("15 deeply nested 4 levels", "<ul><li>1<ul><li>2<ul><li>3<ul><li>4</li></ul></li></ul></li></ul></li></ul>"),
    ("16 empty li between items", "<ul><li>a</li><li></li><li>c</li></ul>"),
    # --- посилання ---
    ("17 link with parens in url", '<p><a href="/wiki/Foo_(bar)">Foo</a></p>'),
    ("18 link with spaces in url", '<p><a href="/a b c.html">sp</a></p>'),
    ("19 mailto and tel", '<p><a href="mailto:a@b.co">mail</a> <a href="tel:+123">call</a></p>'),
    ("20 nested links (invalid html)", '<p><a href="/o">out <a href="/i">in</a></a></p>'),
    ("21 link text is multiline", '<p><a href="/x">line1<br>line2</a></p>'),
    # --- inline / typography ---
    ("22 strong with leading/trailing space", "<p>a <strong> bold </strong> b</p>"),
    ("23 empty strong/em", "<p>x<strong></strong><em>  </em>y</p>"),
    ("24 nbsp and thin spaces", "<p>10&nbsp;000&thinsp;km</p>"),
    ("25 entity soup", "<p>&lt;tag&gt; &amp;amp; &quot;q&quot; &#39;s&#39; &copy;</p>"),
    # --- структура / інші блоки ---
    ("26 hr variants + adjacent text", "<p>above</p><hr><p>below</p>"),
    ("27 figure with figcaption", '<figure><img src="/f.png" alt="f"><figcaption>Cap tion</figcaption></figure>'),
    ("28 iframe/video/audio", '<p>before</p><iframe src="/v"></iframe><video src="/v.mp4"></video><p>after</p>'),
    ("29 svg inline", '<p>ico <svg viewBox="0 0 1 1"><path d="M0 0"/></svg> text</p>'),
    ("30 script/style inside content", "<div>keep<script>var x=1</script><style>.a{}</style>this</div>"),
]

for t, h in CASES:
    print("=" * 70)
    print(t)
    print(repr(c(h)))
