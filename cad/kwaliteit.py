"""Kwaliteitscontrole van een georefereerde tekening, in SQL op ``Ruimte.geom_rd`` (EPSG:28992).

Drie controles, alle drie in PostGIS (de oppervlaktes zijn m2 omdat 28992 in meters is):

1. Geldigheid: ``ST_IsValid`` + ``ST_IsValidReason``. ``ST_MakeValid`` geeft een *voorstel*;
   we slaan het niet automatisch op. Een bowtie (zelfdoorsnijding) heeft meerdere
   herstelmogelijkheden: MakeValid maakt er een MultiPolygon van twee driehoeken van, maar of
   dat is wat de tekenaar bedoelde (een rechthoek met verwisselde hoekpunten) weet alleen die
   tekenaar. Automatisch opslaan zou een tekenfout verstoppen. De oppervlakte voor en na
   laat zien hoe groot dat verschil is: de bowtie telt in ``ST_Area`` bijna 0 (de twee
   driehoeken heffen elkaar op), na MakeValid de som van beide driehoeken.
2. Overlap: self-join op dezelfde tekening, ``a.id < b.id`` (elk paar eenmaal), met
   ``a.geom_rd && b.geom_rd`` (GiST-index) en ``ST_Intersects``; daarna telt alleen
   ``ST_Area(ST_Intersection) > drempel``. Aanraken (gedeelde wand) geeft oppervlakte 0 en valt
   daarmee af. Ongeldige geometrie wordt vooraf met ``ST_MakeValid`` omzeild, anders gooit GEOS
   een TopologyException in ``ST_Intersection``.
3. Plattegrond minus BAG-pand: ``ST_Difference(ST_Union(ruimtes), pand)`` is wat buiten het
   pand steekt; de dekking is ``ST_Area(ST_Intersection) / ST_Area(pand)``.
"""

from django.db import connection

from kaart.models import Pand

STANDAARD_PAND = "0034100000049762"
DREMPEL_M2 = 0.01  # een overlap kleiner dan 1 dm2 is rekenruis van een gedeelde wand

_GELDIG = "CASE WHEN ST_IsValid({c}) THEN {c} ELSE ST_MakeValid({c}) END"


def _rijen(sql: str, params: list) -> list[tuple]:
    with connection.cursor() as c:
        c.execute(sql, params)
        return c.fetchall()


def geldigheid(tekening_id: int) -> list[dict]:
    """Per ruimte: geldig?, reden, oppervlakte voor en na ``ST_MakeValid`` (m2) en het type."""
    sql = """
        SELECT id, nummer, ST_IsValid(geom_rd), ST_IsValidReason(geom_rd), ST_Area(geom_rd),
               ST_Area(ST_MakeValid(geom_rd)), GeometryType(ST_MakeValid(geom_rd))
        FROM cad_ruimte WHERE tekening_id = %s AND geom_rd IS NOT NULL ORDER BY nummer, id
    """
    return [
        {
            "id": i,
            "nummer": n,
            "geldig": g,
            "reden": reden,
            "oppervlakte_voor": voor,
            "oppervlakte_na": na,
            "type_na": t,
        }
        for i, n, g, reden, voor, na, t in _rijen(sql, [tekening_id])
    ]


_A = _GELDIG.format(c="a.geom_rd")
_B = _GELDIG.format(c="b.geom_rd")

OVERLAP_SQL = f"""
    SELECT a.id, a.nummer, b.id, b.nummer,
           ST_Area(ST_Intersection({_A}, {_B}))
    FROM cad_ruimte a JOIN cad_ruimte b
      ON a.tekening_id = b.tekening_id AND a.id < b.id
     AND a.geom_rd && b.geom_rd AND ST_Intersects(a.geom_rd, b.geom_rd)
    WHERE a.tekening_id = %s
      AND ST_Area(ST_Intersection({_A}, {_B})) > %s
    ORDER BY a.nummer, b.nummer
"""


def overlap(tekening_id: int, drempel: float = DREMPEL_M2) -> list[dict]:
    """Paren ruimtes met een overlap groter dan ``drempel`` m2."""
    return [
        {"a_id": ai, "a": an, "b_id": bi, "b": bn, "oppervlakte": opp}
        for ai, an, bi, bn, opp in _rijen(OVERLAP_SQL, [tekening_id, drempel])
    ]


def explain_overlap(tekening_id: int, drempel: float = DREMPEL_M2, zonder_seqscan=False) -> str:
    """``EXPLAIN ANALYZE`` van de overlap-query. Bij een handvol rijen kiest de planner
    een sequentiele scan; ``zonder_seqscan`` zet die uit (alleen in deze transactie) om
    te laten zien dat de GiST-index op ``geom_rd`` bruikbaar is."""
    with connection.cursor() as c:
        c.execute("BEGIN" if connection.get_autocommit() else "SAVEPOINT kwaliteit_explain")
        try:
            if zonder_seqscan:
                c.execute("SET LOCAL enable_seqscan = off")
            c.execute(
                "EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF) " + OVERLAP_SQL, [tekening_id, drempel]
            )
            return "\n".join(r[0] for r in c.fetchall())
        finally:
            c.execute(
                "ROLLBACK" if connection.get_autocommit() else "ROLLBACK TO kwaliteit_explain"
            )


def _pand(pand_id: str) -> Pand:
    try:
        return Pand.objects.get(identificatie=pand_id)
    except Pand.DoesNotExist:
        raise ValueError(f"BAG-pand {pand_id} staat niet in kaart.Pand") from None


def pandverschil(tekening_id: int, pand_id: str = STANDAARD_PAND, geometrie: bool = False) -> dict:
    """Wat steekt van de plattegrond buiten het pand, en hoeveel van het pand is gedekt.

    ``buiten_m2``: ``ST_Area(ST_Difference(unie_ruimtes, pand))``.
    ``dekking_pct``: ``ST_Area(ST_Intersection(unie, pand)) / ST_Area(pand) * 100``.
    ``onbedekt_m2``: ``ST_Area(ST_Difference(pand, unie))`` (pand zonder ruimte).
    Met ``geometrie=True`` komen ook de GeoJSON-geometrieen (RD) van buiten, onbedekt en pand mee.
    """
    pand = _pand(pand_id)
    sql = f"""
        WITH u AS (
            SELECT ST_Union({_GELDIG.format(c="geom_rd")}) AS g FROM cad_ruimte
            WHERE tekening_id = %s AND geom_rd IS NOT NULL
        ), p AS (SELECT geom AS g FROM kaart_pand WHERE id = %s)
        SELECT ST_Area(u.g), ST_Area(p.g), ST_Area(ST_Difference(u.g, p.g)),
               ST_Area(ST_Intersection(u.g, p.g)), ST_Area(ST_Difference(p.g, u.g)),
               ST_AsGeoJSON(ST_Difference(u.g, p.g), 3), ST_AsGeoJSON(ST_Difference(p.g, u.g), 3),
               ST_AsGeoJSON(p.g, 3)
        FROM u, p
    """
    rij = _rijen(sql, [tekening_id, pand.pk])
    if not rij or rij[0][0] is None:
        raise ValueError("geen ruimtes met geom_rd: eerst georefereren")
    plat, pand_m2, buiten, gedekt, onbedekt, g_buiten, g_onbedekt, g_pand = rij[0]
    uit = {
        "pand_id": pand_id,
        "plattegrond_m2": plat,
        "pand_m2": pand_m2,
        "buiten_m2": buiten,
        "onbedekt_m2": onbedekt,
        "dekking_pct": 100 * gedekt / pand_m2,
    }
    if geometrie:
        uit |= {"buiten": g_buiten, "onbedekt": g_onbedekt, "pand": g_pand}
    return uit


def overlap_geometrie(tekening_id: int, drempel: float = DREMPEL_M2) -> list[dict]:
    """Per overlappend paar de intersectiegeometrie als GeoJSON-tekst (RD)."""
    sql = f"""
        SELECT a.nummer, b.nummer,
               ST_Area(i.g), ST_AsGeoJSON(i.g, 3)
        FROM cad_ruimte a JOIN cad_ruimte b
          ON a.tekening_id = b.tekening_id AND a.id < b.id AND a.geom_rd && b.geom_rd
        CROSS JOIN LATERAL (
            SELECT ST_Intersection({_A}, {_B}) AS g
        ) i
        WHERE a.tekening_id = %s
          AND ST_Area(i.g) > %s ORDER BY a.nummer, b.nummer
    """
    return [
        {"a": a, "b": b, "oppervlakte": opp, "geojson": gj}
        for a, b, opp, gj in _rijen(sql, [tekening_id, drempel])
    ]


def controle(tekening_id: int, pand_id: str = STANDAARD_PAND, drempel: float = DREMPEL_M2) -> dict:
    return {
        "geldigheid": geldigheid(tekening_id),
        "overlap": overlap(tekening_id, drempel),
        "pand": pandverschil(tekening_id, pand_id),
    }
