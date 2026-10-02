import { Map, setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre looks for its worker next to its own module, which bundling moves; hand it
// the bundled worker instead.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "./style.css";
import { MAP_CENTER, MAP_ZOOM } from "./config";

/** Same base map as hist_map: OpenFreeMap's positron style, no API key. */
const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/positron";

setWorkerUrl(workerUrl);

// Stage 0: blank base map. Data layers arrive in Stage 8.
new Map({ container: "map", center: MAP_CENTER, zoom: MAP_ZOOM, style: BASEMAP_STYLE });
