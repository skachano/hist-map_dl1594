// Links to places from lists and panels. A territory opens the Territories view in its hierarchy
// and level, with the map fitted to its area; a village picked from the table opens the map zoomed
// in on it. Clicks on the map itself only select: the reader is already looking at the place.
import type { Dataset } from "../data/types";
import { areas } from "../model/territories";
import type { State, Store } from "../state/store";

interface MapFocus {
  zoomTo(placeId: string): void;
  fitArea(placeId: string): void;
}

let focus: MapFocus = { zoomTo: () => {}, fitArea: () => {} };

/** Called once by main with the map, which the views do not hold. */
export function setMapFocus(f: MapFocus): void {
  focus = f;
}

/** Select a place from a link: a territory switches to the Territories view at its hierarchy and level. */
export function openPlace(store: Store, data: Dataset, placeId: string, extra: Partial<State> = {}): void {
  const place = data.places.get(placeId);
  const area = areas(data).find((a) => a.id === placeId);
  if (place?.kind === "territory" && area) {
    focus.fitArea(placeId);
    store.set({ ...extra, view: "territories", place: placeId, feudal: area.hierarchy === "feudal" || undefined,
      kind: undefined,
      level: area.level });
  } else {
    store.set({ ...extra, place: placeId });
  }
}

/** A village picked from a list: the map, zoomed in on it. */
export function showOnMap(store: Store, placeId: string): void {
  focus.zoomTo(placeId);
  store.set({ view: "map", place: placeId });
}
