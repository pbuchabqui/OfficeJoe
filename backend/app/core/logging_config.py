"""
Configuração de logging: humanizado em desenvolvimento, conciso em produção.
"""
from __future__ import annotations

import logging
import logging.config
import sys


def setup_logging() -> None:
    from app.core.config import get_settings
    settings = get_settings()
    is_dev = settings.APP_ENV == "development"

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "dev": {"format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"},
            "prod": {"format": "%(levelname)s | %(name)s | %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "dev" if is_dev else "prod",
                "level": "DEBUG" if is_dev else "INFO",
            }
        },
        "loggers": {
            "officejoe": {
                "handlers": ["console"],
                "level": "DEBUG" if is_dev else "INFO",
                "propagate": False,
            },
            "uvicorn": {"handlers": ["console"], "level": "INFO"},
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "DEBUG" if is_dev else "WARNING",
                "propagate": False,
            },
        },
        "root": {"handlers": ["console"], "level": "WARNING"},
    }
    logging.config.dictConfig(config)
