"""Logging-basis: één plek, console-uitvoer met tijd, niveau en loggernaam."""

import logging
import logging.config

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


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
