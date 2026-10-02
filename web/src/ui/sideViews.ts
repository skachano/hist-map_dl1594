// The side lists beside the map: Territories (one hierarchy, one level), Holders (everything one
// holder holds) and Church & resources (a thematic list of the book, or the chaumes).
import type { Dataset, Entry, Place } from "../data/types";
import { label, name, type StringKey, t } from "../i18n";
import { DISTRICT, REALM_COLOURS } from "../model/colors";
import { currentLevel, levelsOf, realmGroup, shownAreas } from "../model/territories";
import { LAYERS, type Layer, type State, type Store } from "../state/store";
import { fill, h } from "./dom";
import { openPlace, showOnMap } from "./navigate";

/** The thematic lists each Church & resources layer shows. */
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

export function renderTerritoriesView(root: HTMLElement, data: Dataset, state: State, store: Store): void {
  const { lang } = state;
  const feudal = !!state.feudal;
  const levels = levelsOf(data, feudal);
  const level = currentLevel(data, feudal, state.level);
  const shown = shownAreas(data, feudal, level);
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const vocab = data.meta.vocab;
  const sorted = [...shown].sort((a, b) => placeName(a.id).localeCompare(placeName(b.id), lang));
  const swatch = (type: string) => h("span", { class: "swatch",
    style: `--c:${feudal ? REALM_COLOURS[realmGroup(type)] : DISTRICT}` });
  fill(root,
    h("h2", {}, t("view_territories", lang)),
    h("div", { class: "levels", role: "group", "aria-label": t("hierarchy", lang) },
      h("button", { "aria-pressed": String(!feudal), onclick: () => store.set({ feudal: undefined, level: undefined }) },
        t("hierarchyAdmin", lang)),
      h("button", { "aria-pressed": String(feudal), onclick: () => store.set({ feudal: true, level: undefined }) },
        t("hierarchyFeudal", lang))),
    levels.length > 1 ? h("div", { class: "levels", role: "group", "aria-label": t("level", lang) },
      ...[...levels, 0].map((l) => h("button", { "aria-pressed": String(l === level), onclick: () => store.set({ level: l }) },
        t(`level${l}${feudal ? "Feudal" : ""}` as StringKey, lang)))) : null,
    h("p", { class: "key" }, feudal ? t("realmsNote", lang) : t("divisionsNote", lang)),
    h("ul", { class: "realms" }, ...sorted.map((a) => h("li", {},
      swatch(a.type), " ",
      h("button", { class: "link", "data-place": a.id, "aria-pressed": String(state.place === a.id),
        onclick: () => openPlace(store, data, a.id) }, placeName(a.id)),
      h("span", { class: "muted" }, ` · ${label(vocab.territory_types[a.type], lang, a.type)} · ${a.settlements} ${t("places", lang)}`)))),
    h("p", { class: "key" }, t("approxAreas", lang)),
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

export function renderChurchView(root: HTMLElement, data: Dataset, state: State, store: Store): void {
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
    body = [h("p", { class: "key" }, t("chaumesNote", lang)),
      ...[...groups].flatMap(([g, items]) => [
        h("h3", {}, `${t("provostshipOf", lang)} ${g}`),
        h("ul", {}, ...items.map((f) => h("li", {}, h("strong", {}, f.name),
          ` · ${f.attrs?.gistes} ${t("gistes", lang)}`,
          Array.isArray(f.attrs?.also) ? h("span", { class: "muted" }, ` · ${(f.attrs!.also as string[]).join(", ")}`) : "",
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
    h("h2", {}, t("view_church", lang)),
    h("div", { class: "levels", role: "group", "aria-label": t("view_church", lang) },
      ...LAYERS.map((l) => h("button", { "aria-pressed": String(l === layer), onclick: () => store.set({ layer: l }) },
        t(`layer_${l}` as StringKey, lang)))),
    ...body,
  );
}
