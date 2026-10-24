import json

from django.contrib.auth.decorators import login_required
from django.contrib.gis.db.models import Extent
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

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
    return render(request, "cad/tekening.html", {"tekening": obj, "rijen": rijen})


@login_required
def ruimtes_geojson(request, pk):
    obj = get_object_or_404(Tekening, pk=pk)
    ruimtes = list(obj.ruimtes.all())
    features = [
        {
            "type": "Feature",
            "id": r.pk,
            "geometry": json.loads(r.geom.json),
            "properties": {
                "nummer": r.nummer,
                "naam": r.naam,
                "oppervlakte_m2": round(r.oppervlakte_m2, 2),
                "ongeldig": r.geometrie_ongeldig,
            },
        }
        for r in ruimtes
    ]
    extent = obj.ruimtes.aggregate(e=Extent("geom"))["e"] or (0, 0, 10, 10)
    return JsonResponse({"type": "FeatureCollection", "bbox": list(extent), "features": features})
