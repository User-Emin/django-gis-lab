-- Doeltabel voor RVBNAARPOSTGIS (les 35). Coördinaten in EPSG:28992 (RD New).
-- Draai in een schema naar keuze (search_path); PostGIS moet bestaan.
CREATE TABLE IF NOT EXISTS cad_ruimte_import (
    id              bigserial PRIMARY KEY,
    tekening        text        NOT NULL,
    handle          text        NOT NULL,
    laag            text        NOT NULL,
    ruimtenummer    text,
    geom            geometry(Polygon, 28992) NOT NULL,
    geimporteerd_op timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tekening, handle)
);
CREATE INDEX IF NOT EXISTS cad_ruimte_import_geom_gist ON cad_ruimte_import USING gist (geom);
