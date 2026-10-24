from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Buurt, Pand, Project, Tekening


class TekeningInline(admin.TabularInline):
    model = Tekening
    extra = 0


@admin.register(Project)
class ProjectAdmin(GISModelAdmin):
    list_display = ["naam", "opdrachtgever", "status", "aangemaakt"]
    list_filter = ["status"]
    search_fields = ["naam", "opdrachtgever"]
    inlines = [TekeningInline]
    # Kaart start op Almere (lon/lat in graden, de widget rekent zelf om)
    gis_widget_kwargs = {
        "attrs": {"default_lon": 5.2213, "default_lat": 52.3708, "default_zoom": 13}
    }


@admin.register(Tekening)
class TekeningAdmin(admin.ModelAdmin):
    list_display = ["naam", "versie", "project", "geupload_op"]
    list_select_related = ["project"]


@admin.register(Buurt)
class BuurtAdmin(GISModelAdmin):
    list_display = ["buurtnaam", "buurtcode", "aantalinwoners", "dichtheid"]
    search_fields = ["buurtnaam", "buurtcode"]


@admin.register(Pand)
class PandAdmin(GISModelAdmin):
    list_display = ["identificatie", "bouwjaar", "status", "gebruiksdoel"]
    list_filter = ["status"]
    search_fields = ["identificatie"]
    list_per_page = 50
