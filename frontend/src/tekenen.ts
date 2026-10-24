import type Map from "ol/Map";
import type { Polygon } from "ol/geom";
import Draw from "ol/interaction/Draw";
import GeoJSON from "ol/format/GeoJSON";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import { Fill, Stroke, Style } from "ol/style";
import type Feature from "ol/Feature";
import { RD } from "./rd";

/** Waarde van een cookie, bv. `csrftoken` (Django zet die via ensure_csrf_cookie). */
function cookie(naam: string): string {
  const treffer = document.cookie.split("; ").find((c) => c.startsWith(naam + "="));
  return treffer ? decodeURIComponent(treffer.slice(naam.length + 1)) : "";
}

const GEBIED_STIJL = new Style({
  fill: new Fill({ color: "rgba(31, 95, 191, 0.25)" }),
  stroke: new Stroke({ color: "#1f5fbf", width: 3 }),
});
const SCHETS_STIJL = new Style({
  fill: new Fill({ color: "rgba(200, 30, 120, 0.25)" }),
  stroke: new Stroke({ color: "#c81e78", width: 3, lineDash: [6, 4] }),
});

/** Gebieden uit /api/gebieden/ (opgeslagen) en een tekenmodus met opslaan via POST. */
export function startTekenen(kaart: Map, balk: HTMLElement, ingelogd: boolean, gebruiker: string) {
  const formaat = new GeoJSON({ dataProjection: RD, featureProjection: RD });
  const opgeslagen = new VectorSource<Feature>();
  const schets = new VectorSource<Feature>();
  kaart.addLayer(new VectorLayer({ source: opgeslagen, style: GEBIED_STIJL }));
  kaart.addLayer(new VectorLayer({ source: schets, style: SCHETS_STIJL }));

  async function laadGebieden() {
    const r = await fetch("/api/gebieden/?srid=28992");
    opgeslagen.clear();
    opgeslagen.addFeatures(formaat.readFeatures(await r.json()) as Feature[]);
  }

  const kies = document.createElement("select");
  const teken = document.createElement("button");
  const opslaan = document.createElement("button");
  const status = document.createElement("output");
  teken.textContent = "Teken vlak";
  opslaan.textContent = "Opslaan";
  opslaan.disabled = true;
  balk.append(kies, teken, opslaan, status);
  balk.hidden = false;

  fetch("/api/projecten/?page_size=100&srid=28992")
    .then((r) => r.json())
    .then((j) => {
      for (const f of j.features) {
        const o = document.createElement("option");
        o.value = String(f.id);
        o.textContent = f.properties.naam;
        kies.append(o);
      }
    });

  const draw = new Draw({ source: schets, type: "Polygon", style: SCHETS_STIJL });
  draw.setActive(false);
  kaart.addInteraction(draw);
  draw.on("drawstart", () => schets.clear());
  draw.on("drawend", () => {
    draw.setActive(false);
    teken.classList.remove("aan");
    opslaan.disabled = false;
    status.textContent = "Vlak getekend; kies een project en klik Opslaan.";
  });
  teken.addEventListener("click", () => {
    const aan = !draw.getActive();
    draw.setActive(aan);
    teken.classList.toggle("aan", aan);
    status.textContent = aan ? "Klik de hoekpunten; dubbelklik sluit het vlak." : "";
  });

  opslaan.addEventListener("click", async () => {
    const vlak = schets.getFeatures()[0]?.getGeometry() as Polygon | undefined;
    if (!vlak) return;
    const antwoord = await fetch("/api/gebieden/", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": cookie("csrftoken") },
      body: JSON.stringify({
        project: Number(kies.value),
        geometry: JSON.parse(formaat.writeGeometry(vlak)),
      }),
    });
    const tekst = await antwoord.text();
    status.classList.toggle("fout", !antwoord.ok);
    if (antwoord.ok) {
      schets.clear();
      opslaan.disabled = true;
      await laadGebieden();
      status.textContent = `Opgeslagen (${antwoord.status}) als gebied van ${kies.selectedOptions[0].textContent}.`;
    } else {
      status.textContent = `Mislukt: ${antwoord.status} ${tekst.slice(0, 120)}`;
    }
  });

  if (!ingelogd) {
    teken.disabled = true;
    status.textContent = "Inloggen om te tekenen: /admin/login/?next=/kaart/";
  } else {
    status.textContent = `Ingelogd als ${gebruiker}.`;
  }
  laadGebieden();
  (window as unknown as { tekenSchets: VectorSource }).tekenSchets = schets;
}
