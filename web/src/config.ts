/** The single date the source describes: there is no year slider. */
export const YEAR = 1594;

/** Initial view: the whole Duchy of Lorraine, from the Saar to the Vosges. */
export const MAP_CENTER: [number, number] = [6.5, 48.8];
export const MAP_ZOOM = 7.7;
/** Zoom for a place picked from a list: its neighbouring villages in view (max zoom is 13) */
export const PLACE_ZOOM = 12;
/** Zoom for a territory without an area (none of its places located), centred on its own point */
export const TERRITORY_ZOOM = 10;
