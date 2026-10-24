#!/bin/sh
# Maakt data/almere.gpkg uit de lokale database geolab (alleen lezen). Subset: Almere Stad-centrum.
set -e
BBOX="st_makeenvelope(142500,485800,144600,487800,28992)"
SRC="PG:host=127.0.0.1 port=5433 dbname=geolab"
OUT="$(dirname "$0")/../data/almere.gpkg"
rm -f "$OUT"
ogr2ogr -f GPKG "$OUT" "$SRC" -nln panden -nlt MULTIPOLYGON -a_srs EPSG:28992 -sql \
 "select p.gid, p.geom, identificatie, bouwjaar, status, gebruiksdoel, oppervlakte_min, oppervlakte_max, aantal_verblijfsobjecten from almere.panden p where st_intersects(p.geom, $BBOX)"
ogr2ogr -update -f GPKG "$OUT" "$SRC" -nln buurten -nlt MULTIPOLYGON -a_srs EPSG:28992 -sql \
 "select gid, geom, buurtcode, buurtnaam, wijkcode, gemeentecode, gemeentenaam, aantalinwoners, bevolkingsdichtheidinwonersperkm2 as dichtheid, oppervlaktelandinha as landha, jaar from almere.buurten b where st_intersects(b.geom, $BBOX)"
