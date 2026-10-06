// The side lists beside the map: Territories (one hierarchy, one level), Holders (everything one
// holder holds) and, in Settlements, a thematic list of the book or the chaumes.
import type { Dataset, Entry, Place } from "../data/types";
import { label, name, type StringKey, t } from "../i18n";
import { GROUP_COLOUR } from "../model/colors";
import { areas, currentLevel, GROUP_ORDER, KINDS, levelsOf, type RealmGroup, realmGroup, shownAreas } from "../model/territories";
import { type Layer, type State, type Store } from "../state/store";
import { fill, h } from "./dom";
import { openPlace, showOnMap } from "./navigate";

/** The thematic lists each layer of the Settlements tab shows. */
export const LAYER_SERIES: Record<Exclude<Layer, "chaumes">, string[]> = {
  towns: ["towns"],
  churches: ["cathedrals", "collegiates"],
  abbeys: ["abbeys_m", "abbeys_f"],
  priories: ["priories"],
  convents: ["friaries", "convents_m", "grey_sisters", "other_sisters"],
  commanderies: ["commanderies"],
};

/** The entries of a layer, in the book's order. */
export function layerEntries(data: Dataset, layer: Layer): Entry[] {
  if (layer === "chaumes") return [];
  const series = new Set(LAYER_SERIES[layer]);
  return data.entries.filter((e) => e.series && series.has(e.series));
}

const GROUP_LABEL: Record<RealmGroup, StringKey> = {
  bailiwick: "groupBailiwick", office: "groupOffice", county: "groupCounty", lordship: "groupLordship", other: "groupOther" };
const KIND_GROUP_LABEL: Record<(typeof KINDS)[number]["group"], StringKey> = {
  administrative: "kindsAdministrative", feudal: "kindsFeudal" };

/** Territories view, as in hist_map: the hierarchy and level switches, the kind of realm, the colour
 *  key of the kinds shown, and every realm shown with its number of places. */
export function renderTerritoriesView(root: HTMLElement, data: Dataset, state: State, store: Store): void {
  const { lang } = state;
  const feudal = !!state.feudal;
  const levels = levelsOf(data, feudal);
  const level = currentLevel(data, feudal, state.level);
  const shown = shownAreas(data, feudal, level, state.kind);
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const groups = new Map<RealmGroup, number>();
  for (const a of shown) groups.set(realmGroup(a.type), (groups.get(realmGroup(a.type)) ?? 0) + 1);
  const kinds = new Map<string, number>();
  for (const a of areas(data)) kinds.set(a.type, (kinds.get(a.type) ?? 0) + 1);
  const vocab = data.meta.vocab.territory_types;
  const kindLabel = (type: string) => {
    const l = label(vocab[type], lang, type);
    return l.charAt(0).toUpperCase() + l.slice(1);
  };
  const hierarchyButton = (f: boolean, key: StringKey) => h("button",
    { "aria-pressed": String(!state.kind && feudal === f), onclick: () => store.set({ feudal: f || undefined,
      level: undefined, kind: undefined }) }, t(key, lang));
  const levelButton = (l: number) => h("button", { "aria-pressed": String(!state.kind && l === level),
    onclick: () => store.set({ level: l, kind: undefined }) }, t(`level${l}${feudal ? "Feudal" : ""}` as StringKey, lang));
  const kindMenu = h("select", { "aria-label": t("kindOfRealm", lang),
    onchange: (e: Event) => store.set({ kind: (e.target as HTMLSelectElement).value || undefined }) },
    h("option", { value: "", selected: !state.kind }, t("allKinds", lang)),
    ...KINDS.map(({ group, types }) => h("optgroup", { label: t(KIND_GROUP_LABEL[group], lang) },
      ...types.filter((type) => kinds.has(type)).map((type) => h("option", { value: type, selected: type === state.kind },
        `${kindLabel(type)} (${kinds.get(type)})`)))));
  fill(root,
    h("h2", {}, `${t("realmsShown", lang)} (${shown.length})`),
    h("div", { class: "levels hierarchy", role: "group", "aria-label": t("hierarchy", lang) },
      hierarchyButton(false, "hierarchyAdmin"), hierarchyButton(true, "hierarchyFeudal")),
    levels.length > 1 ? h("div", { class: "levels", role: "group", "aria-label": t("level", lang) },
      ...[...levels, 0].map(levelButton)) : null,
    h("label", { class: "kind" }, `${t("kindOfRealm", lang)} `, kindMenu),
    h("ul", { class: "groups" }, ...GROUP_ORDER.map((g) => h("li", {},
      h("span", { class: "swatch", style: `--c:${GROUP_COLOUR[g]}` }), ` ${t(GROUP_LABEL[g], lang)}`,
      h("span", { class: "count" }, ` ${groups.get(g) ?? 0}`)))),
    h("ul", { class: "realms" }, ...[...shown].sort((a, b) => placeName(a.id).localeCompare(placeName(b.id), lang))
      .map((a) => h("li", {},
        h("button", { class: "link", "data-place": a.id, "aria-pressed": String(state.place === a.id),
          onclick: () => openPlace(store, data, a.id) }, placeName(a.id)),
        h("span", { class: "muted" }, a.settlements ? ` · ${a.settlements} ${t("places", lang)}` : ` · ${t("noArea", lang)}`)))),
  );
}

export function renderHoldersView(root: HTMLElement, data: Dataset, state: State, store: Store): void {
  const { lang } = state;
  const entities = [...data.entities.values()].sort((a, b) => a.rank - b.rank);
  const entity = state.entity && data.entities.has(state.entity) ? state.entity : entities[0]?.id;
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const vocab = data.meta.vocab;
  const realms = [...data.places.values()].filter((p) => p.kind === "territory" && p.holder?.includes(entity ?? ""));
  const byTenure = new Map<string, Place[]>();
  for (const p of data.places.values()) {
    for (const x of p.hold ?? []) {
      if (x.h === entity) byTenure.set(x.t, [...(byTenure.get(x.t) ?? []), p]);
    }
  }
  const link = (p: Place) => h("li", {}, h("button", { class: "link", "data-place": p.id,
    onclick: () => openPlace(store, data, p.id) }, placeName(p.id)));
  const byName = (a: Place, b: Place) => placeName(a.id).localeCompare(placeName(b.id), lang);
  fill(root,
    h("h2", {}, t("view_holders", lang)),
    h("label", { class: "kind" }, t("chooseHolder", lang),
      h("select", { onchange: (e: Event) => store.set({ entity: (e.target as HTMLSelectElement).value, place: undefined }) },
        ...entities.map((e) => h("option", { value: e.id, selected: e.id === entity },
          `${name(e.name, lang, e.id)} (${e.holdings})`)))),
    entity ? h("p", { class: "muted" }, label(vocab.entity_types[data.entities.get(entity)!.type], lang)) : null,
    realms.length ? h("h3", {}, t("realmsHeld", lang)) : null,
    realms.length ? h("ul", {}, ...realms.sort(byName).map(link)) : null,
    ...[...byTenure].flatMap(([tenure, places]) => [
      h("h3", {}, `${label(vocab.tenures[tenure], lang, tenure)} (${places.length})`),
      h("ul", { class: "members cols" }, ...places.sort(byName).map(link)),
    ]),
    h("p", { class: "key" }, t("holdersNote", lang)),
  );
}

export function renderLayerView(root: HTMLElement, data: Dataset, state: State, store: Store): void {
  const { lang } = state;
  const layer = state.layer ?? "abbeys";
  const vocab = data.meta.vocab;
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const entryRow = (e: Entry) => h("li", {},
    h("span", { class: "no" }, `${e.no}`), " ",
    e.place ? h("button", { class: "link", "data-place": e.place, onclick: () => showOnMap(store, e.place!) }, e.text)
      : e.text,
    e.place && data.places.get(e.place)?.lat === undefined ? h("span", { class: "muted" }, ` (${t("unlocated", lang)})`) : "",
    e.place && placeName(e.place) !== e.name ? h("span", { class: "muted" }, ` · ${placeName(e.place)}`) : "",
    e.order ? h("span", { class: "muted" }, ` · ${label(vocab.religious_orders[e.order], lang, e.order)}`) : "");
  let body: (HTMLElement | null)[] = [];
  if (layer === "chaumes") {
    const groups = new Map<string, typeof data.features>();
    for (const f of data.features.filter((x) => x.theme === "chaume")) {
      const g = String(f.attrs?.provostship ?? "");
      groups.set(g, [...(groups.get(g) ?? []), f]);
    }
    // other names ("en allemand Mensberg", "aliàs le Hault-Rouan"), one or several
    const also = (f: (typeof data.features)[number]) => [f.attrs?.also ?? []].flat().map(String);
    const gistes = (n: unknown) => n === undefined ? "" : ` · ${n} ${t(n === 1 ? "giste" : "gistes", lang)}`;
    body = [h("p", { class: "key" }, t("chaumesNote", lang)),
      ...[...groups].flatMap(([g, items]) => [
        // the division the heading names ("Sous la prévosté de Sainct-Diey"), in the reader's language
        h("h3", {}, data.places.has(g) ? placeName(g) : `${t("provostshipOf", lang)} ${g}`),
        h("ul", {}, ...items.map((f) => h("li", {}, h("strong", {}, f.name),
          also(f).length ? h("span", {}, ` (${also(f).join(", ")})`) : "",
          gistes(f.attrs?.gistes),
          h("span", { class: "muted" }, ` · ${t("pages", lang)} ${f.page}`)))),
      ])];
  } else {
    const entries = layerEntries(data, layer);
    const groups = new Map<string, Entry[]>();
    for (const e of entries) {
      groups.set(e.series ?? "", [...(groups.get(e.series ?? "") ?? []), e]);
    }
    body = [...groups].flatMap(([series, items]) => [
      h("h3", {}, `${label(vocab.series[series], lang, series)} (${items.length})`),
      h("ul", { class: "entries" }, ...items.map(entryRow))]);
  }
  fill(root,
    h("h2", {}, t(`layer_${layer}` as StringKey, lang)),
    ...body,
  );
}
