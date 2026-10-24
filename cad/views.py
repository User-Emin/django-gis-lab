import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models import Extent
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import kwaliteit
from .forms import UploadForm
from .importeren import ImportFout, importeer_dxf
from .models import Tekening


@login_required
def upload(request):
    """DXF uploaden en importeren. Mislukt de import, dan wordt alles teruggedraaid."""
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                tekening = form.save(commit=False)
                tekening.naam = tekening.naam.strip() or form.cleaned_data["bestand"].name
                tekening.eenheid = "?"
                tekening.save()
                importeer_dxf(tekening.bestand.path, tekening)
        except ImportFout as fout:
            form.add_error("bestand", str(fout))
            # De transactie rolt de rij terug, maar het opgeslagen bestand blijft staan: opruimen.
            tekening.bestand.delete(save=False)
        else:
            return redirect("cad:tekening", pk=tekening.pk)
    return render(request, "cad/upload.html", {"form": form})


RAPPORT_RIJEN = [
    ("geimporteerd", "Geïmporteerd"),
    ("gesloten_gemeld", "Gesloten (open polylijn, gat binnen tolerantie)"),
    ("overgeslagen", "Overgeslagen (open, gat te groot)"),
    ("zonder_nummer", "Zonder nummer"),
    ("ongeldig", "Ongeldige geometrie"),
]


def _regel(item) -> str:
    """Een korte omschrijving van een rapportitem (de vorm verschilt per soort)."""
    if not isinstance(item, dict):
        return str(item)
    naam = item.get("nummer") or item.get("naam") or "zonder nummer"
    extra = item.get("reden") or ""
    if "gat_m" in item:
        extra += f" ({item['gat_m']} m)"
    return f"{naam}: {extra}".strip(": ") if extra else str(naam)


@login_required
def tekening(request, pk):
    obj = get_object_or_404(Tekening, pk=pk)
    r = obj.rapport
    tellingen = {
        "geimporteerd": r.get("aantal_ruimtes", 0),
        **{k: len(r.get(k, [])) for k, _ in RAPPORT_RIJEN[1:]},
    }
    rijen = [(label, tellingen[k], [_regel(i) for i in r.get(k, [])]) for k, label in RAPPORT_RIJEN]
    # Op de PDOK-kaart (RD) zodra geom_rd gevuld is; ?crs=lokaal forceert de lokale weergave.
    rd = _heeft_rd(obj) and request.GET.get("crs") != "lokaal"
    return render(request, "cad/tekening.html", {"tekening": obj, "rijen": rijen, "rd": rd})


def _heeft_rd(obj) -> bool:
    return obj.ruimtes.filter(geom_rd__isnull=False).exists()


@login_required
def ruimtes_geojson(request, pk):
    """Ruimtes als GeoJSON. Standaard lokaal (SRID 990001); ``?crs=rd`` geeft geom_rd (28992)."""
    obj = get_object_or_404(Tekening, pk=pk)
    rd = request.GET.get("crs") == "rd"
    if rd and not _heeft_rd(obj):
        return JsonResponse({"fout": "tekening is niet gegeorefereerd (geom_rd leeg)"}, status=409)
    veld = "geom_rd" if rd else "geom"
    ruimtes = [r for r in obj.ruimtes.all() if getattr(r, veld) is not None]
    features = [
        {
            "type": "Feature",
            "id": r.pk,
            "geometry": json.loads(getattr(r, veld).json),
            "properties": {
                "nummer": r.nummer,
                "naam": r.naam,
                "oppervlakte_m2": round(r.oppervlakte_m2, 2),
                "ongeldig": r.geometrie_ongeldig,
            },
        }
        for r in ruimtes
    ]
    extent = obj.ruimtes.aggregate(e=Extent(veld))["e"] or (0, 0, 10, 10)
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "crs": "EPSG:28992" if rd else "LOKAAL:990001",
            "bbox": list(extent),
            "features": features,
        }
    )


@login_required
def fouten_geojson(request, pk):
    """Foutvlakken in RD: overlap (intersectie per paar), buiten het pand, pand zonder ruimte,
    plus het BAG-pand zelf. Een FeatureCollection; ``properties.soort`` zegt wat het is."""
    obj = get_object_or_404(Tekening, pk=pk)
    if not _heeft_rd(obj):
        return JsonResponse({"fout": "tekening is niet gegeorefereerd (geom_rd leeg)"}, status=409)
    pand_id = request.GET.get("pand") or obj.bag_pand_id or kwaliteit.STANDAARD_PAND
    features = []

    def voeg_toe(soort, geojson, **props):
        features.append(
            {
                "type": "Feature",
                "geometry": json.loads(geojson),
                "properties": {"soort": soort, **props},
            }
        )

    for o in kwaliteit.overlap_geometrie(obj.pk):
        voeg_toe(
            "overlap", o["geojson"], tussen=f"{o['a']} / {o['b']}", m2=round(o["oppervlakte"], 2)
        )
    samenvatting = {
        "ongeldig": [r["nummer"] for r in kwaliteit.geldigheid(obj.pk) if not r["geldig"]]
    }
    try:
        p = kwaliteit.pandverschil(obj.pk, pand_id, geometrie=True)
    except ValueError as fout:
        samenvatting["pand"] = str(fout)
    else:
        voeg_toe("pand", p["pand"], pand_id=pand_id, m2=round(p["pand_m2"], 2))
        if p["buiten_m2"] > kwaliteit.DREMPEL_M2:
            voeg_toe("buiten", p["buiten"], m2=round(p["buiten_m2"], 2))
        samenvatting["pand"] = {
            "buiten_m2": round(p["buiten_m2"], 2),
            "dekking_pct": round(p["dekking_pct"], 1),
        }
    samenvatting["overlap"] = [
        f["properties"] for f in features if f["properties"]["soort"] == "overlap"
    ]
    return JsonResponse(
        {
            "type": "FeatureCollection",
            "crs": "EPSG:28992",
            "samenvatting": samenvatting,
            "features": features,
        }
    )


def taak_status(request, taak_id):
    """Status van een Celery-taak als HTML, of JSON met ``?format=json``."""
    from celery.result import AsyncResult

    res = AsyncResult(taak_id)
    data = {"id": taak_id, "status": res.status}
    if res.successful():
        data["resultaat"] = res.result
    elif res.failed():
        data["fout"] = str(res.result)
    if request.GET.get("format") == "json":
        return JsonResponse(data)
    return render(request, "cad/taak.html", {"taak": data})
