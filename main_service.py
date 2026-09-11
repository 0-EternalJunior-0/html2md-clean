"""CLI та фасад для конвертації HTML у Markdown.

Точка входу: `HTMLToMarkdownConverter` (програмний API) або запуск модуля як
скрипт для обробки файлу / stdin.
"""

from typing import Optional

from markdown.generator import MarkdownGenerator
from markdown.options import MarkdownOptions


class HTMLToMarkdownConverter:
    """Сервіс конвертації HTML → Markdown з очищенням шуму.

    Приклад:
        converter = HTMLToMarkdownConverter()
        markdown = converter.convert(html)
    """

    def __init__(self, options: Optional[MarkdownOptions] = None):
        self.options = options or self._build_default_options()
        self.generator = MarkdownGenerator(self.options)

    @staticmethod
    def _build_default_options() -> MarkdownOptions:
        """Дефолти під web-scraping: агресивніше очищення шуму, коротші пороги.

        Перелічені ЛИШЕ відхилення від дефолтів ``MarkdownOptions``.
        """
        return MarkdownOptions(
            include_links=False,
            remove_nav=False,
            remove_header=False,
            remove_aside=False,
            min_paragraph_length=5,
            min_heading_length=1,
            generate_citations=True,
            link_density_threshold=0.6,
            min_content_words=20,
            max_length=200000,
            noise_classes=frozenset({
                "ad", "ads", "advertisement", "banner", "cookie", "popup", "modal",
                "overlay", "newsletter", "subscribe", "social", "share", "sponsored",
                "carousel", "promo", "disclaimer"
            }),
            noise_tags=frozenset({
                "script", "style", "noscript", "template", "svg", "canvas",
                "iframe", "embed", "object", "video", "audio",
                "select", "option", "optgroup"
            }),
            noise_ids=frozenset({"cookie", "popup", "modal", "overlay", "newsletter", "ads"}),
        )

    def convert(self, html: str) -> str:
        """Повертає ``fit_markdown`` для заданого HTML."""
        result = self.generator.generate_from_html(html)
        return result.fit_markdown


def main() -> None:
    """CLI-точка входу: читає HTML з файлу/stdin і пише Markdown у файл/stdout."""
    import argparse
    import pathlib
    import sys

    parser = argparse.ArgumentParser(
        prog="main_service",
        description="HTML → Markdown конвертер.",
    )
    parser.add_argument(
        "input",
        type=pathlib.Path,
        nargs="?",
        help="Шлях до HTML-файлу. Якщо не задано — читаємо з stdin.",
    )
    parser.add_argument(
        "--include-links",
        action="store_true",
        help="Зберігати гіперпосилання у markdown (за замовч. вимкнено).",
    )
    parser.add_argument(
        "--force-bs4",
        action="store_true",
        help="Форсувати BeautifulSoup-адаптер замість Selectolax.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=None,
        help="Файл для запису Markdown. За замовч. — stdout.",
    )
    args = parser.parse_args()

    html_content = (
        args.input.read_text(encoding="utf-8")
        if args.input
        else sys.stdin.read()
    )

    options = HTMLToMarkdownConverter._build_default_options()
    if args.include_links:
        options = options.with_overrides(include_links=True)
    if args.force_bs4:
        options = options.with_overrides(force_beautifulsoup=True)

    converter = HTMLToMarkdownConverter(options)
    md = converter.convert(html_content)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
    else:
        print(md)


if __name__ == "__main__":
    main()
