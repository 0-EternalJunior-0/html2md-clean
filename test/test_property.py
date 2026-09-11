"""AUDIT_04 Б13 — property-based тести конвертера через hypothesis.

Dev-only: `hypothesis` НЕ додається у `requirements.txt`. Якщо пакета немає —
модуль пропускається цілком.

Перевіряються властивості, які мають виконуватись для БУДЬ-ЯКОГО входу:
1. no-crash на fuzz-HTML (включно з битою розміткою);
2. idempotency-подібна стабільність (той самий вхід → той самий вихід);
3. subset-of-text: видимий текст із HTML присутній у markdown.
"""

import pytest

hypothesis = pytest.importorskip("hypothesis", reason="hypothesis — dev-залежність")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from markdown import MarkdownGenerator, MarkdownOptions  # noqa: E402

# Спільні налаштування: конвертація великих дерев повільна, тож обмежуємо
# кількість прикладів і вимикаємо too_slow-хелсчек.
_SETTINGS = settings(
    max_examples=60,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

# Теги, з яких збираємо fuzz-документи — суміш блокових, інлайнових,
# табличних і тих, що конвертер спеціально обробляє.
_TAGS = [
    "p", "div", "span", "h1", "h2", "h3", "ul", "ol", "li", "a", "img",
    "table", "tr", "td", "th", "pre", "code", "blockquote", "br", "hr",
    "strong", "em", "nav", "footer", "aside", "script", "style",
]

# Текст без символів, що керують розміткою — щоб властивість subset
# перевіряла саме конвертацію, а не екранування.
_safe_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs", "Cc"),
        blacklist_characters="<>&\\`*_[]()#|~\r\n\t",
    ),
    min_size=1,
    max_size=40,
)


@st.composite
def fuzz_html(draw):
    """Генерує (можливо невалідний) HTML: незакриті теги, порожні атрибути тощо."""
    parts = []
    for _ in range(draw(st.integers(min_value=1, max_value=8))):
        tag = draw(st.sampled_from(_TAGS))
        text = draw(st.text(max_size=30))
        closed = draw(st.booleans())
        attrs = draw(
            st.sampled_from(
                ['', ' class="x"', ' id="ad-banner"', ' href=""', ' src=""', ' hidden']
            )
        )
        parts.append(f"<{tag}{attrs}>{text}" + (f"</{tag}>" if closed else ""))
    return "".join(parts)


@given(fuzz_html())
@_SETTINGS
def test_convert_never_crashes(html):
    """Property: жоден fuzz-HTML не має валити конвертер."""
    result = MarkdownGenerator().generate_from_html(html)
    assert isinstance(result.fit_markdown, str)
    assert isinstance(result.text, str)


@given(fuzz_html())
@_SETTINGS
def test_convert_is_deterministic(html):
    """Property: конвертація чиста — той самий вхід дає той самий вихід."""
    first = MarkdownGenerator().generate_from_html(html)
    second = MarkdownGenerator().generate_from_html(html)
    assert first.fit_markdown == second.fit_markdown
    assert first.text == second.text


@given(st.lists(_safe_text, min_size=1, max_size=6))
@_SETTINGS
def test_paragraph_text_is_preserved(paragraphs):
    """Property (subset-of-text): текст простих <p> доходить до markdown.

    Використовуємо `<article>`, щоб main-content-евристика не відкинула блок.
    `min_paragraph_length=0` — свідомо: дефолтні 3 символи відкидають короткі
    параграфи (це задокументована фіча, а не втрата даних), і без цього
    hypothesis миттєво знаходить контрприклад `["0"]`.
    """
    html = "<html><body><article>" + "".join(
        f"<p>{p}</p>" for p in paragraphs
    ) + "</article></body></html>"

    options = MarkdownOptions(min_paragraph_length=0)
    result = MarkdownGenerator(options).generate_from_html(html)

    for paragraph in paragraphs:
        stripped = paragraph.strip()
        # Порожні/пробільні параграфи конвертер свідомо викидає.
        if not stripped:
            continue
        # Нормалізація пробілів: конвертер схлопує послідовні пробіли.
        expected = " ".join(stripped.split())
        if not expected:
            continue
        assert expected in " ".join(result.fit_markdown.split())


@given(fuzz_html())
@_SETTINGS
def test_scripts_never_leak_into_output(html):
    """Property: вміст <script>/<style> ніколи не потрапляє у markdown."""
    payload = "SECRETPAYLOAD"
    doc = f"<html><body><script>{payload}</script><style>{payload}</style>{html}</body></html>"
    result = MarkdownGenerator(MarkdownOptions()).generate_from_html(doc)
    assert payload not in result.fit_markdown
    assert payload not in result.text
