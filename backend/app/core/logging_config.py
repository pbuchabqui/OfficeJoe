"""
Configuração de logging estruturado (JSON em produção, humanizado em dev).
"""
from __future__ import annotations

import logging
import logging.config
import sys
from typing import Any, Dict

from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    is_dev = settings.APP_ENV == "development"

    fmt_standard = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    fmt_audit = (
        "%(asctime)s | AUDIT | %(levelname)-8s | %(name)s | %(message)s | audit_id=%(audit_id)s"
    )

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": fmt_standard},
            "audit": {
                "()": "logging.Formatter",
                "fmt": fmt_audit,
                "defaults": {"audit_id": "-"},
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "standard",
                "level": "DEBUG" if is_dev else "INFO",
            },
            "audit_console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "audit",
                "level": "INFO",
            },
        },
        "loggers": {
            "officejoe": {
                "handlers": ["console"],
                "level": "DEBUG" if is_dev else "INFO",
                "propagate": False,
            },
            "officejoe.audit": {
                "handlers": ["audit_console"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn": {"handlers": ["console"], "level": "INFO"},
            "celery": {"handlers": ["console"], "level": "INFO"},
            "sqlalchemy.engine": {
                "handlers": ["console"],
                "level": "DEBUG" if is_dev else "WARNING",
                "propagate": False,
            },
        },
        "root": {"handlers": ["console"], "level": "WARNING"},
    }
    logging.config.dictConfig(config)
