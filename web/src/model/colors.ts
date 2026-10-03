// Map colours. A choropleth puts every colour next to every other, and only three categorical
// colours stay distinguishable for colour-blind readers in that setting (validated in hist_map
// with the dataviz palette checker, all pairs, light surface). So each view uses at most three
// colours plus a neutral grey; tooltip, legend and panel always name what a colour stands for.
export const SERIES = ["#2a78d6", "#eb6834", "#1baf7a"];
export const OTHER = "#c3c2b7";
/** Territories only: the other realms (bans, mairies, vals, church lands). The neutral grey OTHER
 *  vanishes on the grey basemap at the areas' opacity; this is the palette's darker muted neutral. */
export const REALM_OTHER = "#898781";

/** Tenure: ducal domain, fiefs, church lands; safeguards share the neutral grey. */
export const TENURE_COLOURS: Record<string, string> = {
  domain: SERIES[0], fief: SERIES[1], clergy: SERIES[2], safeguard: OTHER,
};
/** Territories: the colour of each kind of realm, as in hist_map (model/territories.ts groups the types). */
/** Bailliages: hist_map's fourth hue (its marquisates), violet, the one fourth hue that validates
 *  all-pairs against SERIES and OTHER on a map (dataviz checker: worst CVD ΔE 9.2, normal vision 16.3). */
export const BAILIWICK = "#4a3aa7";
export const GROUP_COLOUR = { bailiwick: BAILIWICK, office: SERIES[0], lordship: SERIES[1], county: SERIES[2],
  other: REALM_OTHER } as const;
