import "ol/ol.css";
import Map from "ol/Map";
import View from "ol/View";
import GeoJSON from "ol/format/GeoJSON";
import VectorLayer from "ol/layer/Vector";
import VectorSource from "ol/source/Vector";
import Projection from "ol/proj/Projection";
import { Fill, Stroke, Style, Text } from "ol/style";
import type { FeatureLike } from "ol/Feature";

// Les 18: een lokaal assenstelsel (meters), zonder ondergrond. De code is vrij gekozen en
// komt overeen met SRID 990001 in PostGIS; OpenLayers rekent er niet naartoe om.
const doel = document.getElementById("plattegrond")!;

function stijl(f: FeatureLike): Style {
  const ongeldig = f.get("ongeldig") === true;
  return new Style({
    fill: new Fill({ color: ongeldig ? "rgba(200, 30, 30, 0.45)" : "rgba(60, 120, 190, 0.25)" }),
    stroke: new Stroke({ color: ongeldig ? "#b3261e" : "#2c5a8c", width: ongeldig ? 3 : 1.5, lineDash: ongeldig ? [6, 4] : undefined }),
    text: new Text({
      text: (f.get("nummer") as string) || "?",
      font: "bold 13px system-ui, sans-serif",
      fill: new Fill({ color: ongeldig ? "#7a0f0a" : "#102a43" }),
      stroke: new Stroke({ color: "#fff", width: 3 }),
      overflow: true,
    }),
  });
}

async function start() {
  const json = await (await fetch(doel.dataset.url!)).json();
  const extent = json.bbox as [number, number, number, number];
  const lokaal = new Projection({ code: "LOKAAL:990001", units: "m", extent });
  const formaat = new GeoJSON({ dataProjection: lokaal, featureProjection: lokaal });
  const bron = new VectorSource({ features: formaat.readFeatures(json) });
  const kaart = new Map({
    target: doel,
    layers: [new VectorLayer({ source: bron, style: stijl })],
    view: new View({ projection: lokaal, center: [0, 0], zoom: 0 }),
  });
  kaart.getView().fit(extent, { padding: [30, 30, 30, 30] });
  (window as unknown as Record<string, unknown>).plattegrond = kaart;
  kaart.once("rendercomplete", () => doel.setAttribute("data-klaar", "ja"));
}
start();
