"""Registreer het lokale tekenstelsel (meters) in PostGIS' ``spatial_ref_sys``."""

from django.db import migrations

SRID = 990001
WKT = 'LOCAL_CS["Tekening lokaal (meters)",LOCAL_DATUM["Tekening",0],UNIT["metre",1],AXIS["X",EAST],AXIS["Y",NORTH]]'


def toevoegen(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute(
            "INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) "
            "VALUES (%s, 'LAB', %s, %s, '') ON CONFLICT (srid) DO NOTHING",
            [SRID, SRID, WKT],
        )


def weghalen(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute("DELETE FROM spatial_ref_sys WHERE srid = %s", [SRID])


class Migration(migrations.Migration):
    dependencies = [("cad", "0001_initial")]
    operations = [migrations.RunPython(toevoegen, weghalen)]
