from django.contrib import admin

from .models import Project, Tekening


class TekeningInline(admin.TabularInline):
    model = Tekening
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["naam", "opdrachtgever", "status", "aangemaakt"]
    list_filter = ["status"]
    search_fields = ["naam", "opdrachtgever"]
    inlines = [TekeningInline]


@admin.register(Tekening)
class TekeningAdmin(admin.ModelAdmin):
    list_display = ["naam", "versie", "project", "geupload_op"]
    list_select_related = ["project"]
