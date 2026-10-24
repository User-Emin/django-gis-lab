import proj4 from "proj4";
import { register } from "ol/proj/proj4";
import { get as getProjection } from "ol/proj";
import TileLayer from "ol/layer/Tile";
import WMTS from "ol/source/WMTS";
import WMTSTileGrid from "ol/tilegrid/WMTS";

// EPSG:28992 (Amersfoort / RD New) kent OpenLayers niet zelf: proj4-definitie (epsg.io) registreren.
proj4.defs(
  "EPSG:28992",
  "+proj=sterea +lat_0=52.1561605555556 +lon_0=5.38763888888889 +k=0.9999079 " +
    "+x_0=155000 +y_0=463000 +ellps=bessel " +
    "+towgs84=565.4171,50.3319,465.5524,1.9342,-1.6677,9.1019,4.0725 +units=m +no_defs",
);
register(proj4);

export const RD = getProjection("EPSG:28992")!;
// Geldigheidsgebied van de PDOK-tilematrix (TopLeftCorner -285401.92 903401.92, 15 niveaus)
RD.setExtent([-285401.92, 22598.08, 595401.92, 903401.92]);

// Uit de WMTS-capabilities van PDOK: niveau 00 heeft ScaleDenominator 12288000 en elke stap halveert.
const PIXEL = 0.00028; // OGC-standaardpixel in meters
export const RESOLUTIONS = Array.from({ length: 15 }, (_, i) => (12288000 * PIXEL) / 2 ** i);
export const MATRIX_IDS = RESOLUTIONS.map((_, i) => String(i).padStart(2, "0"));

export function brtAchtergrond(laag = "standaard"): TileLayer<WMTS> {
  return new TileLayer({
    source: new WMTS({
      url: `https://service.pdok.nl/kadaster/brt-achtergrondkaart/wmts/v2_0/${laag}/{TileMatrixSet}/{TileMatrix}/{TileCol}/{TileRow}.png`,
      layer: laag,
      matrixSet: "EPSG:28992",
      style: "default",
      format: "image/png",
      requestEncoding: "REST",
      projection: RD,
      tileGrid: new WMTSTileGrid({
        origin: [-285401.92, 903401.92],
        resolutions: RESOLUTIONS,
        matrixIds: MATRIX_IDS,
      }),
      attributions: "Kaartgegevens © Kadaster (BRT Achtergrondkaart, PDOK)",
    }),
  });
}
