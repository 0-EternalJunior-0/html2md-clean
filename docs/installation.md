# Встановлення

Потрібен **Python 3.11+**.

## З PyPI

```bash
pip install html2md-clean
```

## З опційними «батарейками»

Дати, санітизація HTML, лікування encoding, очищення URL, boilerplate-екстракція:

```bash
pip install "html2md-clean[full]"
```

## Для розробки

```bash
pip install "html2md-clean[dev]"
# або з усім:
pip install "html2md-clean[full,dev]"
```

## З GitLab

```bash
pip install git+https://gitlab.com/demoprogrammer/html2md-clean.git
```

## Editable-режим із сирців

```bash
git clone https://gitlab.com/demoprogrammer/html2md-clean.git
cd html2md-clean
python -m venv .venv && source .venv/bin/activate
pip install -e ".[full,dev]"
```

## Опційні залежності

| Можливість | Опція `MarkdownOptions` | Пакет |
| --- | --- | --- |
| Витяг дат | `extract_dates` | `htmldate` |
| Санітизація HTML | `sanitize_html` | `nh3` |
| Лікування mojibake | `fix_text_encoding` | `ftfy` |
| Очищення URL | `clean_urls` | `courlan` |
| Boilerplate-екстракція | `use_trafilatura_extraction` | `trafilatura` |
| Швидкий парсер (авто) | — | `selectolax` |

Якщо опційний пакет відсутній — відповідна функція просто пропускається
(graceful degradation), конвертація не переривається.
