"""Live-перевірка конвертера на реальних (складних, «захищених» динамічною
розміткою) сторінках: Wikipedia, Amazon, BBC, Hacker News тощо.

Ці тести звертаються до мережі й автоматично **пропускаються**, якщо мережі
немає або сайт недоступний/віддав не-200 — щоб офлайн-CI не падав. Перевіряємо
не байт-у-байт (сторінки змінюються), а інваріанти якості:

- конвертація не падає й повертає непорожній Markdown;
- заголовок сторінки витягнуто;
- розумна кількість слів (сторінка не «схлопнулась» у кілька токенів);
- КОЖНА згенерована таблиця має стабільну ширину колонок (rowspan/colspan
  не зсунули дані) — головний тест на пошкодження таблиць у продакшені.
"""

import re
import socket
import ssl
import urllib.request

import pytest

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _network_available() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 443), timeout=3).close()
        return True
    except OSError:
        return False


NETWORK = _network_available()
pytestmark = pytest.mark.skipif(not NETWORK, reason="немає доступу до мережі")


def _fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        if resp.status != 200:
            pytest.skip(f"{url} → HTTP {resp.status}")
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, "ignore")


def _fetch_or_skip(url: str) -> str:
    try:
        return _fetch(url)
    except Exception as e:  # noqa: BLE001 — будь-яка мережна проблема → skip
        pytest.skip(f"недоступно {url}: {type(e).__name__}: {e}")


def _pipe_count(line: str) -> int:
    """Кількість НЕекранованих `|` (роздільники колонок)."""
    return len(re.findall(r"(?<!\\)\|", line))


def _assert_all_tables_consistent(md: str) -> int:
    """Кожна суміжна група `|`-рядків має однакову ширину. Повертає к-сть таблиць."""
    blocks, blk = [], []
    for ln in md.split("\n"):
        if ln.strip().startswith("|"):
            blk.append(ln)
        elif blk:
            blocks.append(blk)
            blk = []
    if blk:
        blocks.append(blk)

    for b in blocks:
        counts = {_pipe_count(ln) for ln in b}
        assert len(counts) == 1, (
            f"нестабільна ширина таблиці ({counts}) — можливе зсування даних:\n"
            + "\n".join(b[:8])
        )
    return len(blocks)


REAL_PAGES = [
    ("wikipedia_article", "https://en.wikipedia.org/wiki/Python_(programming_language)"),
    ("wikipedia_big_tables", "https://en.wikipedia.org/wiki/List_of_countries_by_GDP_(nominal)"),
    ("amazon_home", "https://www.amazon.com/"),
    ("bbc_news", "https://www.bbc.com/news"),
    ("hacker_news", "https://news.ycombinator.com/"),
]


class TestRealPages:

    @pytest.mark.parametrize("name,url", REAL_PAGES, ids=[p[0] for p in REAL_PAGES])
    def test_page_converts_without_data_corruption(self, name, url):
        html = _fetch_or_skip(url)
        assert len(html) > 1000, f"підозріло короткий HTML з {url}"

        opts = MarkdownOptions(include_tables=True, include_links=True)
        res = MarkdownGenerator(opts).generate_from_html(html)
        md = res.fit_markdown

        assert isinstance(md, str) and md.strip(), "порожній markdown"
        assert res.title, "не витягнуто <title>"
        assert res.word_count > 20, f"занадто мало слів: {res.word_count}"

        # Головний інваріант: жодна таблиця не «розлізлась» по колонках.
        _assert_all_tables_consistent(md)

    def test_wikipedia_gdp_tables_present_and_aligned(self):
        # Сторінка з великими багатоярусними таблицями (rowspan/colspan у thead).
        html = _fetch_or_skip(REAL_PAGES[1][1])
        md = MarkdownGenerator(MarkdownOptions(include_tables=True)).generate_from_html(html).fit_markdown
        n_tables = _assert_all_tables_consistent(md)
        assert n_tables >= 1, "очікували принаймні одну таблицю на GDP-сторінці"
        # Сепаратор GFM присутній → таблиці реально згенеровано.
        assert re.search(r"\| --- \|", md)
