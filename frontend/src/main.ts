import "ol/ol.css";
import Map from "ol/Map";
import View from "ol/View";
import Overlay from "ol/Overlay";
import GeoJSON from "ol/format/GeoJSON";
import VectorLayer from "ol/layer/Vector";
import TileLayer from "ol/layer/Tile";
import type WMTS from "ol/source/WMTS";
import OSM from "ol/source/OSM";
import VectorSource from "ol/source/Vector";
import { bbox as bboxStrategy } from "ol/loadingstrategy";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style";
import type { FeatureLike } from "ol/Feature";
import type Feature from "ol/Feature";
import { RESOLUTIONS, RD, brtAchtergrond } from "./rd";

// Project 1 (centroid van een pand in Almere Centrum), RD-meters
const CENTRUM: [number, number] = [143515.95, 486811.47];
// Met ?fout=geen-projectie laten we de View bewust zonder projectie (dus Web Mercator) draaien.
const FOUT = new URLSearchParams(location.search).get("fout") === "geen-projectie";

/** GeoJSON-bron die per bbox de API aanroept (srid=28992 = zelfde stelsel als de kaart). */
function apiBron(pad: string, extra = ""): VectorSource {
  const formaat = new GeoJSON(FOUT ? {} : { dataProjection: RD, featureProjection: RD });
  const bron = new VectorSource<Feature>({ format: formaat, strategy: bboxStrategy });
  bron.setLoader(async (extent, resolution) => {
    if (resolution > 2) return []; // te ver uitgezoomd: duizenden panden laden heeft geen zin
    let url: string | null =
      `${pad}?srid=28992&page_size=500&bbox_modus=overlap&in_bbox=${extent.map(Math.round).join(",")}${extra}`;
    const features: Feature[] = [];
    while (url) {
      const antwoord = await fetch(url);
      if (!antwoord.ok) throw new Error(`${url}: ${antwoord.status}`);
      const json = await antwoord.json();
      features.push(...(formaat.readFeatures(json) as Feature[]));
      url = json.next ? new URL(json.next).pathname + new URL(json.next).search : null;
    }
    return features;
  });
  return bron;
}

const panden = new VectorLayer({
  source: apiBron("/api/panden/"),
  style: new Style({
    fill: new Fill({ color: "rgba(214, 90, 40, 0.35)" }),
    stroke: new Stroke({ color: "#a33d12", width: 1 }),
  }),
});
// Zelf les 14: buurtlaag onder de panden; een klik buiten een pand toont de buurtnaam
const buurten = new VectorLayer({
  source: apiBron("/api/buurten/"),
  style: new Style({
    fill: new Fill({ color: "rgba(40, 120, 90, 0.08)" }),
    stroke: new Stroke({ color: "#1c6b4f", width: 2.5, lineDash: [8, 5] }),
  }),
});
const projecten = new VectorLayer({
  source: apiBron("/api/projecten/"),
  style: new Style({
    image: new CircleStyle({
      radius: 9,
      fill: new Fill({ color: "#1f5fbf" }),
      stroke: new Stroke({ color: "#fff", width: 2.5 }),
    }),
  }),
});

const achtergrond = FOUT ? new TileLayer({ source: new OSM() }) : brtAchtergrond();
// Zelf les 14: laagwisselaar (standaard/grijs/pastel) via de laag-parameter van brtAchtergrond
const ACHTERGRONDEN = ["standaard", "grijs", "pastel"];
const startLaag = new URLSearchParams(location.search).get("laag") ?? "standaard";
let huidige: TileLayer<WMTS> = achtergrond as TileLayer<WMTS>;
const view = FOUT
  ? new View({ center: CENTRUM, zoom: 12 }) // de fout: RD-meters als Web Mercator-meters
  : new View({ projection: RD, center: CENTRUM, resolutions: RESOLUTIONS, zoom: 12 });

const kaart = new Map({
  target: "kaart",
  layers: [achtergrond, buurten, panden, projecten],
  view,
});

// Klik -> popup (textContent, nooit innerHTML: de attributen komen uit de database)
const popupEl = document.getElementById("popup")!;
const popup = new Overlay({ element: popupEl, positioning: "bottom-center", stopEvent: true,
  autoPan: { animation: { duration: 0 }, margin: 30 } });
kaart.addOverlay(popup);

function toonPopup(f: FeatureLike, coord: number[]) {
  const p = f.getProperties();
  popupEl.replaceChildren();
  const kop = document.createElement("h3");
  kop.textContent = p.naam
    ? `Project: ${p.naam}`
    : p.buurtnaam
      ? `Buurt: ${p.buurtnaam}`
      : `Pand ${p.identificatie}`;
  const lijst = document.createElement("dl");
  const velden: [string, unknown][] = p.naam
    ? [["Opdrachtgever", p.opdrachtgever], ["Status", p.status]]
    : p.buurtnaam
      ? [["Buurtcode", p.buurtcode], ["Inwoners", p.aantalinwoners], ["Dichtheid", p.dichtheid]]
      : [["Bouwjaar", p.bouwjaar], ["Status", p.status], ["Gebruiksdoel", p.gebruiksdoel ?? "onbekend"]];
  for (const [k, v] of velden) {
    const dt = document.createElement("dt"); dt.textContent = k;
    const dd = document.createElement("dd"); dd.textContent = String(v);
    lijst.append(dt, dd);
  }
  popupEl.append(kop, lijst);
  popupEl.hidden = false;
  popup.setPosition(coord);
}

kaart.on("singleclick", (e) => {
  // Projecten liggen bovenop de panden: eerste treffer wint
  const f = kaart.forEachFeatureAtPixel(e.pixel, (feat) => feat, { hitTolerance: 4 });
  if (f) toonPopup(f, e.coordinate);
  else { popup.setPosition(undefined); popupEl.hidden = true; }
});
kaart.on("pointermove", (e) => {
  const doel = kaart.getTargetElement();
  if (doel) doel.style.cursor = kaart.hasFeatureAtPixel(e.pixel) ? "pointer" : "";
});

// Laagwisselaar-knoppen
if (!FOUT) {
  const balk = document.getElementById("lagen")!;
  const wissel = (naam: string) => {
    kaart.getLayers().remove(huidige);
    huidige = brtAchtergrond(naam);
    kaart.getLayers().insertAt(0, huidige);
    balk.querySelectorAll("button").forEach((b) => b.classList.toggle("aan", b.dataset.laag === naam));
  };
  for (const naam of ACHTERGRONDEN) {
    const b = document.createElement("button");
    b.textContent = naam; b.dataset.laag = naam;
    b.addEventListener("click", () => wissel(naam));
    balk.append(b);
  }
  wissel(startLaag);
}

// Statusregel: stelsel, zoomniveau, resolutie
const info = document.getElementById("info")!;
function werkInfoBij() {
  const c = (view.getCenter() ?? []).map((v) => Math.round(v)).join(", ");
  info.textContent = `${view.getProjection().getCode()} · zoom ${view.getZoom()?.toFixed(1)} · ${view.getResolution()?.toFixed(2)} m/px · midden ${c}`;
}
view.on("change", werkInfoBij);
werkInfoBij();

// Klaarsignaal voor screenshots: alle tegels en features geladen
(window as unknown as { kaartKlaar: () => boolean }).kaartKlaar = () =>
  !kaart.getAllLayers().some((l) => (l.getSource() as { loading?: boolean } | null)?.loading) &&
  !(huidige.getSource() as unknown as { getState(): string }).getState().includes("loading");
(window as unknown as { kaart: Map }).kaart = kaart;
