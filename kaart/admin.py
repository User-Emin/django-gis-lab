from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.contrib.gis.db.models.functions import Area

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


ALMERE_KAART = {"attrs": {"default_lon": 5.2213, "default_lat": 52.3708, "default_zoom": 13}}


class BouwperiodeFilter(admin.SimpleListFilter):
    title = "bouwperiode"
    parameter_name = "periode"

    def lookups(self, request, model_admin):
        return [
            ("tot1990", "voor 1990"),
            ("1990", "1990-1999"),
            ("2000", "2000-2009"),
            ("2010", "vanaf 2010"),
        ]

    def queryset(self, request, queryset):
        grenzen = {
            "tot1990": {"bouwjaar__lt": 1990},
            "1990": {"bouwjaar__gte": 1990, "bouwjaar__lt": 2000},
            "2000": {"bouwjaar__gte": 2000, "bouwjaar__lt": 2010},
            "2010": {"bouwjaar__gte": 2010},
        }
        return queryset.filter(**grenzen[self.value()]) if self.value() in grenzen else queryset


@admin.register(Buurt)
class BuurtAdmin(GISModelAdmin):
    list_display = ["buurtnaam", "buurtcode", "aantalinwoners", "dichtheid"]
    search_fields = ["buurtnaam", "buurtcode"]
    gis_widget_kwargs = ALMERE_KAART


@admin.register(Pand)
class PandAdmin(GISModelAdmin):
    list_display = ["identificatie", "bouwjaar", "oppervlak_m2", "status", "gebruiksdoel"]
    list_filter = ["status", BouwperiodeFilter]
    search_fields = ["identificatie"]
    list_per_page = 50
    exclude = ["midden_wgs", "midden_geo"]
    gis_widget_kwargs = ALMERE_KAART

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_opp=Area("geom"))

    @admin.display(description="oppervlak (m2)", ordering="_opp")
    def oppervlak_m2(self, obj):
        return round(obj._opp.sq_m)
