"""python manage.py georefereer <tekening_id> --paspunten <json> [--soort affien|helmert] [--droog]

Schat de transformatie lokaal -> RD uit paspunten, print de restfouten en (zonder --droog)
vult ``Ruimte.geom_rd``. Het JSON-bestand is een lijst of een object met sleutel "paspunten";
elk punt heeft "naam", "rd_m" en "lokaal_m" of "lokaal_mm" (zoals georef-waarheid.json).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cad import georef
from cad.models import Tekening


def lees_paspunten(pad: Path) -> list[dict]:
    data = json.loads(pad.read_text())
    if isinstance(data, dict):
        data = data["paspunten"]
    uit = []
    for p in data:
        if "lokaal_mm" in p:
            lokaal = [w / 1000 for w in p["lokaal_mm"]]
        else:
            lokaal = list(p["lokaal_m"])
        uit.append({"naam": p["naam"], "lokaal": lokaal, "rd": list(p["rd_m"])})
    return uit


class Command(BaseCommand):
    help = "Georefereer een tekening met paspunten (kleinste kwadraten) en vul geom_rd."

    def add_arguments(self, parser):
        parser.add_argument("tekening_id", type=int)
        parser.add_argument("--paspunten", type=Path, required=True)
        parser.add_argument("--soort", choices=["affien", "helmert"], default="affien")
        parser.add_argument("--droog", action="store_true", help="alleen meten, niets opslaan")

    def handle(self, *args, tekening_id, paspunten, soort, droog, **opties):
        try:
            tekening = Tekening.objects.get(pk=tekening_id)
        except Tekening.DoesNotExist:
            raise CommandError(f"tekening {tekening_id} bestaat niet") from None
        punten = lees_paspunten(paspunten)
        try:
            r = georef.bereken(punten, soort)
        except ValueError as fout:
            raise CommandError(str(fout)) from fout
        w = self.stdout.write
        w(f"Tekening {tekening.pk} ({tekening.naam}), {soort}, {len(punten)} paspunten")
        w(f"{'punt':<5}{'residu (m)':>12}{'zonder dit punt (m)':>22}")
        for p, res, loo in zip(punten, r.residuen, r.leave_one_out, strict=True):
            loo_t = "-" if loo is None else f"{loo:.4f}"
            w(f"{p['naam']:<5}{res:>12.4f}{loo_t:>22}")
        a, b, c, d, e, f = r.matrix
        w(f"RMSE        {r.rmse:.4f} m")
        w(f"rotatie     {r.rotatie_graden:.4f} graden")
        w(f"schaal      x {r.schaal_x:.6f}  y {r.schaal_y:.6f}")
        w(f"verschuiving {r.verschuiving[0]:.4f}, {r.verschuiving[1]:.4f} (RD van lokaal 0,0)")
        w(f"matrix      a={a:.8f} b={b:.8f} c={c:.4f} d={d:.8f} e={e:.8f} f={f:.4f}")
        if len(punten) < 4:
            w("LET OP: bij 3 punten is de restfout altijd 0; dat is geen controle.")
        grootste = max(range(len(punten)), key=lambda i: r.residuen[i])
        w(f"grootste residu: punt {punten[grootste]['naam']} ({r.residuen[grootste]:.4f} m)")
        if droog:
            w("Droog: niets opgeslagen")
            return
        with transaction.atomic():
            n = 0
            for ruimte in tekening.ruimtes.all():
                ruimte.geom_rd = georef.pas_toe(ruimte.geom, r.matrix)
                ruimte.save(update_fields=["geom_rd"])
                n += 1
            tekening.paspunten = punten
            tekening.georef = {
                "soort": soort,
                "matrix": list(r.matrix),
                "rmse_m": r.rmse,
                "rotatie_graden": r.rotatie_graden,
                "schaal_x": r.schaal_x,
                "schaal_y": r.schaal_y,
                "residuen_m": r.residuen,
            }
            tekening.save(update_fields=["paspunten", "georef"])
        w(f"geom_rd gevuld voor {n} ruimtes (SRID 28992)")
