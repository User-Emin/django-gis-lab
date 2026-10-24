"""Template-tags: zet de gehashte bestanden uit Vite's manifest.json in de pagina."""

import json
from functools import lru_cache

from django import template
from django.conf import settings
from django.templatetags.static import static
from django.utils.html import format_html, format_html_join

register = template.Library()


@lru_cache
def _manifest(pad: str, mtime: float) -> dict:
    with open(pad) as f:
        return json.load(f)


def laad_manifest() -> dict:
    pad = settings.VITE_MANIFEST
    try:
        return _manifest(str(pad), pad.stat().st_mtime)
    except FileNotFoundError:
        raise template.TemplateSyntaxError(
            f"{pad} ontbreekt: draai eerst `npm run build` in frontend/"
        ) from None


@register.simple_tag
def vite_css(entry: str):
    """<link>-tags voor de CSS van een entry."""
    manifest = laad_manifest()
    bestanden: list[str] = []

    def verzamel(sleutel: str):
        # Met twee entries delen die een chunk (ol); de CSS van gedeelde chunks hoort er ook bij.
        for naam in manifest[sleutel].get("imports", []):
            verzamel(naam)
        bestanden.extend(b for b in manifest[sleutel].get("css", []) if b not in bestanden)

    verzamel(entry)
    return format_html_join(
        "\n", '<link rel="stylesheet" href="{}">', ((static(f"app/{b}"),) for b in bestanden)
    )


@register.simple_tag
def vite_js(entry: str):
    """<script type=module> voor een entry."""
    return format_html(
        '<script type="module" src="{}"></script>', static("app/" + laad_manifest()[entry]["file"])
    )
