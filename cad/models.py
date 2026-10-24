"""Een geimporteerde plattegrond (``Tekening``) en zijn ruimtes (``Ruimte``).

Opslag van lokale coordinaten (keuze les 18)
--------------------------------------------
Een DXF heeft een lokaal assenstelsel in meters (na omrekenen via ``$INSUNITS``), nog niet
gekoppeld aan de wereld. Wij slaan dat op in ``Ruimte.geom`` in een eigen, door ons
gedefinieerd lokaal stelsel: SRID ``LOKAAL_SRID`` (990001, in PostGIS' vrije gebruikersbereik
910000-998999), met een rij in ``spatial_ref_sys`` (migratie 0002, ``LOCAL_CS`` in meters).

Waarom niet ``srid=0`` (PostGIS' "onbekend vlak stelsel")? Dat is gemeten (``_shots/txt/r18-01``):
``PolygonField(srid=0)`` maakt wel de kolom ``geometry(Polygon,0)``, maar opslaan faalt met
``ST_Transform: 0 is an invalid target SRID``. GEOS rapporteert SRID 0 als ``None``; Django ziet
dan een verschil met het veld-SRID en wikkelt de waarde in ``ST_Transform(..., 0)``. Met een
eigen SRID werkt een gewone ``Polygon(..., srid=LOKAAL_SRID)`` zonder omweg.

Gevolgen: afstanden en oppervlaktes (``ST_Area``) zijn in meters; ``ST_Transform`` naar
een ander stelsel kan niet (geen transformatie gedefinieerd); lokaal en 28992 mengen kan niet.
Daarom heeft ``Ruimte`` een tweede, nullable veld ``geom_rd`` (EPSG:28992). Les 19 georefereert
de lokale meters daarheen (verschuiven/draaien) en vult dat veld; tot dan blijft het leeg.
"""

from django.contrib.gis.db import models

LOKAAL_SRID = 990001


class Tekening(models.Model):
    bestand = models.FileField(upload_to="tekeningen/")
    naam = models.CharField(max_length=200)
    bag_pand_id = models.CharField(max_length=16, blank=True)
    eenheid = models.CharField(max_length=10, help_text="Uit $INSUNITS, bv. 'mm'")
    geupload_op = models.DateTimeField(auto_now_add=True)
    rapport = models.JSONField(default=dict, blank=True)
    # Les 19. Paspunten: [{naam, lokaal: [x, y] m, rd: [x, y] m}]. Bewust JSON op Tekening en
    # geen eigen model: ze horen bij precies een tekening, worden altijd als hele set gelezen
    # en nooit los bevraagd of gejoind; een FK-model zou alleen extra rijen en een join geven.
    paspunten = models.JSONField(default=list, blank=True)
    # Uitkomst van georefereer: soort, matrix, rmse, rotatie, schaal, residuen.
    georef = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-geupload_op"]

    def __str__(self):
        return self.naam


class Ruimte(models.Model):
    tekening = models.ForeignKey(Tekening, on_delete=models.CASCADE, related_name="ruimtes")
    nummer = models.CharField(max_length=20, blank=True)
    naam = models.CharField(max_length=100, blank=True)
    laag = models.CharField(max_length=100)
    oppervlakte_m2 = models.FloatField()
    # Lokale tekeningcoordinaten in meters (SRID LOKAAL_SRID). Zie de moduletekst.
    geom = models.PolygonField(srid=LOKAAL_SRID)
    # Gevuld in les 19 na georefereren naar EPSG:28992.
    geom_rd = models.PolygonField(srid=28992, null=True, blank=True)
    # Les 18 slaat ook ongeldige geometrie op (zelfdoorsnijding, ...); les 19 controleert.
    geometrie_ongeldig = models.BooleanField(default=False)

    class Meta:
        ordering = ["nummer", "pk"]

    def __str__(self):
        return f"{self.nummer or '?'} {self.naam}".strip()
