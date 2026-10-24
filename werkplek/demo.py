"""Kleine demo: type hints en logging."""

import logging

from projectkaart.logging_config import configure_logging

log = logging.getLogger(__name__)


def oppervlakte(breedte_m: float, lengte_m: float) -> float:
    """Oppervlakte van een rechthoek in m²."""
    return breedte_m * lengte_m


if __name__ == "__main__":
    configure_logging("DEBUG")
    log.debug("start demo")
    log.info("oppervlakte: %.1f m2", oppervlakte(12.5, 8.0))
    log.warning("dit is een waarschuwing")
