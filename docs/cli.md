# CLI

Після встановлення пакета доступна команда `html2md`.

## Використання

```bash
# з файлу у stdout
html2md page.html

# зі stdin у файл
cat page.html | html2md -o page.md

# зберегти посилання (у CLI-профілі вони вимкнені за замовчуванням)
html2md page.html --include-links

# форсувати BeautifulSoup замість Selectolax
html2md page.html --force-bs4
```

## Аргументи

| Аргумент | Опис |
| --- | --- |
| `input` | Шлях до HTML-файлу. Якщо не задано — читання зі stdin. |
| `-o`, `--output` | Файл для запису Markdown. За замовчуванням — stdout. |
| `--include-links` | Зберігати гіперпосилання в Markdown. |
| `--force-bs4` | Форсувати BeautifulSoup-адаптер замість Selectolax. |

## Запуск без встановлення

Прямо з репозиторію (як модуль):

```bash
python main_service.py page.html -o page.md
```

!!! note "CLI-профіль"
    CLI використовує агресивніші дефолти під web-scraping
    (`HTMLToMarkdownConverter`): активніше очищення шуму та коротші пороги
    довжини абзаців/заголовків.
