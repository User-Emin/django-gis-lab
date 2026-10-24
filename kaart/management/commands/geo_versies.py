import ctypes

from django.contrib.gis import gdal, geos
from django.contrib.gis.gdal import libgdal
from django.core.management.base import BaseCommand
from django.db import connection


def proj_versie() -> str:
    major, minor, patch = (ctypes.c_int() for _ in range(3))
    libgdal.lgdal.OSRGetPROJVersion(ctypes.byref(major), ctypes.byref(minor), ctypes.byref(patch))
    return f"{major.value}.{minor.value}.{patch.value}"


class Command(BaseCommand):
    help = "Toon welke GDAL/GEOS/PROJ/PostGIS-versies Django gebruikt (les 09)."

    def handle(self, *args, **options):
        self.stdout.write(f"GDAL    {gdal.gdal_version().decode()}")
        self.stdout.write(f"GEOS    {geos.geos_version().decode()}")
        self.stdout.write(f"PROJ    {proj_versie()}")
        with connection.cursor() as cur:
            cur.execute("select postgis_lib_version()")
            self.stdout.write(f"PostGIS {cur.fetchone()[0]}")
