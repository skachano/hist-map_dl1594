// Map colours. A choropleth puts every colour next to every other, and only three categorical
// colours stay distinguishable for colour-blind readers in that setting (validated in hist_map
// with the dataviz palette checker, all pairs, light surface). So each view uses at most three
// colours plus a neutral grey; tooltip, legend and panel always name what a colour stands for.
export const SERIES = ["#2a78d6", "#eb6834", "#1baf7a"];
export const OTHER = "#c3c2b7";
/** Area fill for administrative divisions: the palette's darker muted neutral (the grey OTHER vanishes
 *  on the grey basemap at the areas' opacity). */
export const DISTRICT = "#898781";

/** Tenure: ducal domain, fiefs, church lands; safeguards share the neutral grey. */
export const TENURE_COLOURS: Record<string, string> = {
  domain: SERIES[0], fief: SERIES[1], clergy: SERIES[2], safeguard: OTHER,
};
/** Kinds of realm: church lands, lordships (terres, seigneuries, fiefs), counties. */
export const REALM_COLOURS: Record<string, string> = {
  temporality: SERIES[2], lordship: SERIES[1], county: SERIES[0],
};
