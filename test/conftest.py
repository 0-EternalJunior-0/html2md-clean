"""Test configuration for html2md-clean."""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest  # noqa: E402
from markdown.options import MarkdownOptions  # noqa: E402, F401
from markdown.generator import MarkdownGenerator  # noqa: E402, F401

WEBMAINBENCH_DIR = os.path.join(os.path.dirname(__file__), "data", "webmainbench")


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def default_options():
    """Default MarkdownOptions."""
    return MarkdownOptions()


@pytest.fixture
def minimal_options():
    """Options with everything stripped down."""
    return MarkdownOptions(
        remove_nav=False,
        remove_header=False,
        remove_footer=False,
        remove_aside=False,
        remove_ads=False,
        remove_scripts=False,
        remove_buttons=False,
        include_links=False,
        include_images=False,
        include_tables=False,
        include_code_blocks=False,
        include_lists=False,
        include_blockquotes=False,
        min_paragraph_length=0,
        min_heading_length=0,
    )


@pytest.fixture
def generator():
    """Default MarkdownGenerator."""
    return MarkdownGenerator()


@pytest.fixture
def bs4_generator():
    """MarkdownGenerator forced to use BeautifulSoup."""
    return MarkdownGenerator(MarkdownOptions(force_beautifulsoup=True))


@pytest.fixture
def simple_html():
    """Simple, minimal HTML document for basic tests."""
    return """<!DOCTYPE html>
<html lang="en">
<head><title>Test Page</title></head>
<body>
    <h1>Main Title</h1>
    <p>This is a paragraph with <strong>bold</strong> and <em>italic</em> text.</p>
    <h2>Section One</h2>
    <p>Another paragraph here with <code>inline code</code>.</p>
    <a href="https://example.com">Example Link</a>
</body>
</html>"""


@pytest.fixture
def complex_html():
    """Complex HTML with many element types."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Complex Page</title>
    <meta name="description" content="A complex test page">
</head>
<body>
    <nav><ul><li><a href="/home">Home</a></li><li><a href="/about">About</a></li></ul></nav>
    <header><h1>Site Header</h1></header>
    <article>
        <h1>Main Article Title</h1>
        <p>This is the main content of the article with several paragraphs.</p>
        <h2>Subsection</h2>
        <p>More content in this subsection that should be preserved.</p>
        <h3>Details</h3>
        <ul>
            <li>Item one</li>
            <li>Item two</li>
            <li>Item three</li>
        </ul>
        <ol>
            <li>First</li>
            <li>Second</li>
            <li>Third</li>
        </ol>
        <blockquote>
            <p>This is a blockquote with important information.</p>
        </blockquote>
        <pre><code class="language-python">def hello():
    print("world")</code></pre>
        <table>
            <thead>
                <tr><th>Name</th><th>Value</th></tr>
            </thead>
            <tbody>
                <tr><td>Alpha</td><td>1</td></tr>
                <tr><td>Beta</td><td>2</td></tr>
            </tbody>
        </table>
        <img src="/image.jpg" alt="Test Image">
        <hr>
        <p><a href="https://example.com">External Link</a></p>
    </article>
    <aside><p>Sidebar content</p></aside>
    <footer><p>Footer content &copy; 2024</p></footer>
    <script>console.log('remove me');</script>
    <style>.hidden { display: none; }</style>
</body>
</html>"""


@pytest.fixture
def nav_heavy_html():
    """HTML with navigation, header, footer that should be removed."""
    return """<!DOCTYPE html>
<html>
<head><title>Nav Heavy</title></head>
<body>
    <nav class="main-nav">
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
    </nav>
    <header class="site-header">
        <h1>Site Name</h1>
    </header>
    <main>
        <h1>Real Content</h1>
        <p>This is the actual content that should remain after cleaning.</p>
    </main>
    <aside class="sidebar">
        <p>Sidebar with links</p>
    </aside>
    <footer class="site-footer">
        <p>&copy; 2024 Site</p>
    </footer>
</body>
</html>"""


@pytest.fixture
def ad_heavy_html():
    """HTML with ad/popup/cookie elements."""
    return """<!DOCTYPE html>
<html>
<head><title>Ad Heavy</title></head>
<body>
    <div class="ad banner">Ad banner content</div>
    <div id="cookie" class="cookie popup">Cookie consent text</div>
    <div class="newsletter">Subscribe to our newsletter</div>
    <div class="social share">Share buttons</div>
    <div class="comments">Comment section here</div>
    <div class="related">Related articles</div>
    <main>
        <h1>Main Content</h1>
        <p>This is the real content of the page.</p>
    </main>
</body>
</html>"""


@pytest.fixture
def table_html():
    """HTML with various table configurations."""
    return """<!DOCTYPE html>
<html>
<head><title>Tables</title></head>
<body>
    <h1>Table Tests</h1>
    <table>
        <thead>
            <tr>
                <th>Col A</th>
                <th>Col B</th>
                <th>Col C</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1|1</td>
                <td>1,2</td>
                <td>1 3</td>
            </tr>
            <tr>
                <td>2.1</td>
                <td colspan="2">spanned</td>
            </tr>
            <tr>
                <td>3.1</td>
                <td>3.2</td>
                <td>multi
line cell</td>
            </tr>
        </tbody>
    </table>
    <table>
        <tr><td>Simple A</td><td>Simple B</td></tr>
        <tr><td>Val 1</td><td>Val 2</td></tr>
    </table>
</body>
</html>"""


@pytest.fixture
def code_html():
    """HTML with code blocks in various languages."""
    return """<!DOCTYPE html>
<html>
<head><title>Code</title></head>
<body>
    <h1>Code Examples</h1>
    <pre><code>plain code block</code></pre>
    <pre><code class="language-python">import os
print("hello")</code></pre>
    <pre><code class="lang-javascript">const x = 42;</code></pre>
    <pre><code>various languages</code></pre>
    <p>Inline <code>code here</code> in paragraph.</p>
</body>
</html>"""


@pytest.fixture
def list_html():
    """HTML with various list types including task lists."""
    return """<!DOCTYPE html>
<html>
<head><title>Lists</title></head>
<body>
    <h1>List Tests</h1>
    <ul>
        <li>Unordered item 1</li>
        <li>Unordered item 2</li>
        <li>Unordered item 3</li>
    </ul>
    <ol>
        <li>Ordered item 1</li>
        <li>Ordered item 2</li>
        <li>Ordered item 3</li>
    </ol>
    <ul>
        <li>Parent
            <ul>
                <li>Child 1</li>
                <li>Child 2</li>
                <li>Child 3
                    <ul>
                        <li>Grandchild</li>
                    </ul>
                </li>
            </ul>
        </li>
    </ul>
    <ul>
        <li><input type="checkbox" checked> Done task</li>
        <li><input type="checkbox"> Undone task</li>
        <li><input type="checkbox" checked> Another done</li>
    </ul>
    <dl>
        <dt>Term 1</dt>
        <dd>Definition 1</dd>
        <dt>Term 2</dt>
        <dd>Definition 2a</dd>
        <dd>Definition 2b</dd>
    </dl>
</body>
</html>"""


@pytest.fixture
def inline_formatting_html():
    """HTML with inline formatting elements."""
    return """<!DOCTYPE html>
<html>
<head><title>Inline Formatting</title></head>
<body>
    <p><strong>Bold text</strong></p>
    <p><b>Also bold</b></p>
    <p><em>Italic text</em></p>
    <p><i>Also italic</i></p>
    <p><code>Inline code</code></p>
    <p><del>Strikethrough</del></p>
    <p><s>Also strikethrough</s></p>
    <p><strike>Third strikethrough</strike></p>
    <p><a href="https://example.com">Link text</a></p>
    <p>Line one<br>Line two<br/>Line three</p>
    <p>Mixed <strong>bold</strong> and <em>italic</em> and <code>code</code> together.</p>
    <p>HTML entities: &amp; &lt; &gt; &quot; &copy;</p>
</body>
</html>"""


@pytest.fixture
def image_html():
    """HTML with image elements."""
    return """<!DOCTYPE html>
<html>
<head><title>Images</title></head>
<body>
    <h1>Image Tests</h1>
    <img src="/images/photo.jpg" alt="A photo">
    <img src="https://example.com/img.png" alt="External image">
    <img src="/relative/path.gif" alt="">
    <img alt="No src attribute">
    <img src="data:image/png;base64,abc123" alt="Data URI">
</body>
</html>"""


@pytest.fixture
def noise_html():
    """HTML with various noise elements to test removal."""
    return """<!DOCTYPE html>
<html>
<head><title>Noise</title></head>
<body>
    <script type="text/javascript">var x = 1;</script>
    <style>.hidden { display: none; }</style>
    <noscript>JavaScript is required.</noscript>
    <template><div>Template content</div></template>
    <svg width="100"><circle r="50"/></svg>
    <iframe src="https://example.com"></iframe>
    <video src="movie.mp4"></video>
    <audio src="sound.mp3"></audio>
    <canvas id="myCanvas"></canvas>
    <button>Click me</button>
    <form action="/submit"><input type="text"></form>
    <main>
        <h1>Content</h1>
        <p>Actual content here.</p>
    </main>
</body>
</html>"""


@pytest.fixture
def blockquote_html():
    """HTML with blockquotes."""
    return """<!DOCTYPE html>
<html>
<head><title>Blockquotes</title></head>
<body>
    <blockquote>
        <p>Simple quote</p>
    </blockquote>
    <blockquote>
        <p>First paragraph of quote</p>
        <p>Second paragraph of quote</p>
    </blockquote>
    <blockquote>
        <p>Quote with <strong>bold</strong> and <em>italic</em></p>
    </blockquote>
</body>
</html>"""


@pytest.fixture
def hr_html():
    """HTML with horizontal rules."""
    return """<!DOCTYPE html>
<html>
<head><title>HR</title></head>
<body>
    <p>Before</p>
    <hr>
    <p>After</p>
    <hr/>
    <p>End</p>
</body>
</html>"""


@pytest.fixture
def container_html():
    """HTML with div/section containers for mixed content tests."""
    return """<!DOCTYPE html>
<html>
<head><title>Containers</title></head>
<body>
    <div>
        <p>Paragraph in div.</p>
    </div>
    <div>
        <h2>Heading in div</h2>
        <p>Text after heading.</p>
    </div>
    <div>
        <strong>Title:</strong> Some text here
        <p>Another paragraph.</p>
    </div>
    <section>
        <h3>Section heading</h3>
        <p>Section paragraph.</p>
    </section>
</body>
</html>"""


@pytest.fixture
def url_html():
    """HTML with various link types for URL normalization tests."""
    return """<!DOCTYPE html>
<html>
<head><title>URLs</title></head>
<body>
    <a href="https://example.com/page">Absolute HTTPS</a>
    <a href="http://example.com/page">Absolute HTTP</a>
    <a href="/relative/path">Relative path</a>
    <a href="relative/file.html">Relative file</a>
    <a href="../parent/dir">Parent directory</a>
    <a href="#anchor">Anchor only</a>
    <a href="mailto:user@example.com">Email</a>
    <a href="tel:+1234567890">Phone</a>
    <a href="javascript:void(0)">JavaScript</a>
</body>
</html>"""


@pytest.fixture
def special_chars_html():
    """HTML with special characters that need escaping."""
    return """<!DOCTYPE html>
<html>
<head><title>Special Chars</title></head>
<body>
    <p>Text with * asterisks</p>
    <p>Text with _ underscores</p>
    <p>Text with [brackets]</p>
    <p>Text with (parens)</p>
    <p>Text with # hash</p>
    <p>Text with + plus</p>
    <p>Text with - dash</p>
    <p>Text with ! exclaim</p>
    <p>Text with ~ tilde</p>
    <p>Text with | pipe</p>
    <table>
        <tr><td>Cell with | pipe</td><td>Normal</td></tr>
    </table>
</body>
</html>"""


@pytest.fixture
def webmainbench_pages():
    """Load metadata for downloaded WebMainBench pages."""
    meta_files = []
    if os.path.exists(WEBMAINBENCH_DIR):
        for fname in sorted(os.listdir(WEBMAINBENCH_DIR)):
            if fname.endswith("_meta.json"):
                meta_path = os.path.join(WEBMAINBENCH_DIR, fname)
                html_path = meta_path.replace("_meta.json", ".html")
                if os.path.exists(html_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta_files.append({
                        "html_path": html_path,
                        "meta": meta,
                        "fname": fname.replace("_meta.json", ""),
                    })
    return meta_files


@pytest.fixture
def webmainbench_html(webmainbench_pages):
    """Return list of (html_content, metadata) tuples for all downloaded pages."""
    results = []
    for page in webmainbench_pages:
        with open(page["html_path"], "r", encoding="utf-8") as f:
            html = f.read()
        results.append((html, page["meta"]))
    return results
