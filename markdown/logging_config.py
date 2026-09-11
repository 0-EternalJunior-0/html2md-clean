"""Опційна конфігурація логування для пакета ``markdown``.

За замовчуванням до логера пакета приєднано ``logging.NullHandler`` (у
``markdown/__init__.py``), тож бібліотека нічого не пише сама. Застосунок,
якому потрібен діагностичний вивід, викликає ``configure_logging()``.
"""

from __future__ import annotations

import logging
from logging.config import dictConfig

_PACKAGE_LOGGER = "markdown"


def configure_logging(level: int | str = logging.WARNING) -> None:
    """Налаштовує вивід логів пакета ``markdown`` у stderr на заданому рівні."""
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "markdown_default": {
                    "format": "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                    "datefmt": "%H:%M:%S",
                }
            },
            "handlers": {
                "markdown_console": {
                    "class": "logging.StreamHandler",
                    "formatter": "markdown_default",
                    "stream": "ext://sys.stderr",
                }
            },
            "loggers": {
                _PACKAGE_LOGGER: {
                    "handlers": ["markdown_console"],
                    "level": level,
                    "propagate": False,
                }
            },
        }
    )
