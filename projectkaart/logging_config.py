"""Logging-basis: één plek, console-uitvoer met tijd, niveau en loggernaam.

Les 27: ``JsonFormatter`` schrijft één JSON-object per regel (voor log-aggregatie).
Prod gebruikt hem.
"""

import json
import logging
import logging.config
from datetime import UTC, datetime

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

_STANDAARD = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Tijd, niveau, logger, bericht, plus alle ``extra=``-velden en een eventuele traceback."""

    def format(self, record: logging.LogRecord) -> str:
        regel = {
            "tijd": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "niveau": record.levelname,
            "logger": record.name,
            "bericht": record.getMessage(),
        }
        regel.update({k: v for k, v in vars(record).items() if k not in _STANDAARD})
        if record.exc_info:
            regel["uitzondering"] = self.formatException(record.exc_info)
        return json.dumps(regel, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"basis": {"format": LOG_FORMAT}},
            "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "basis"}},
            "root": {"handlers": ["console"], "level": level},
        }
    )
