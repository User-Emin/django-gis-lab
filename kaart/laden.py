"""Laad data/almere.gpkg (BAG-panden, CBS-buurten) in PostGIS met LayerMapping."""

from pathlib import Path

from django.contrib.gis.utils import LayerMapping

GPKG = Path(__file__).resolve().parent.parent / "data" / "almere.gpkg"

buurt_mapping = {
    "gid": "gid",
    "buurtcode": "buurtcode",
    "buurtnaam": "buurtnaam",
    "wijkcode": "wijkcode",
    "gemeentecode": "gemeentecode",
    "gemeentenaam": "gemeentenaam",
    "aantalinwoners": "aantalinwoners",
    "dichtheid": "dichtheid",
    "landha": "landha",
    "jaar": "jaar",
    "geom": "MULTIPOLYGON",
}

pand_mapping = {
    "gid": "gid",
    "identificatie": "identificatie",
    "bouwjaar": "bouwjaar",
    "status": "status",
    "gebruiksdoel": "gebruiksdoel",
    "oppervlakte_min": "oppervlakte_min",
    "oppervlakte_max": "oppervlakte_max",
    "aantal_verblijfsobjecten": "aantal_verblijfsobjecten",
    "geom": "MULTIPOLYGON",
}


def laad(model, mapping, laag, bron=GPKG, verbose=False):
    """Eén laag laden; transform=False want bron en kolom zijn beide EPSG:28992."""
    lm = LayerMapping(model, str(bron), mapping, layer=laag, transform=False, encoding="utf-8")
    lm.save(strict=True, verbose=verbose)
