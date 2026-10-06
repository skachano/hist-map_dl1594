// Application state, mirrored in the URL hash so any view can be linked:
//   #/map?lang=fr&place=saint-avold   (the Settlements tab; links with the old colour modes still open it)
//   #/map?layer=abbeys (the Settlements tab showing a thematic list instead of the tenures; old #/church links open it)
//   #/territories?h=feudal&lvl=1   #/territories?kind=provostship     #/holders?entity=abbey-saint-avold
//   #/table?d=provostship-nancy&t=fief&q=chasteau      #/table?o=-place (sorted by place, descending)
import type { Lang } from "../data/types";
import { LANGS } from "../i18n";

/** In the header's order; Settlements (the map) is the default. */
export const VIEWS = ["map", "territories", "holders", "table", "about"] as const;
export type View = (typeof VIEWS)[number];
export const LAYERS = ["towns", "churches", "abbeys", "priories", "convents", "commanderies", "chaumes"] as const;
export type Layer = (typeof LAYERS)[number];

/** The Table's columns it sorts by; the entry number is the default order. */
export const SORT_COLUMNS = ["type", "no", "place", "district", "tenure", "alix", "index"] as const;
export type SortColumn = (typeof SORT_COLUMNS)[number];

export interface TableFilters {
  /** a division (with its sub-divisions) */
  district?: string;
  /** a realm */
  realm?: string;
  /** a section of the Dénombrement: domain, fief, clergy, safeguard, other */
  section?: string;
  holder?: string;
  /** "main" (the Dénombrement), or a thematic list */
  series?: string;
  /** words in the entry's text */
  q?: string;
}

export interface State {
  view: View;
  lang: Lang;
  place?: string;
  /** territories view: which hierarchy, and which level (0 = all); or one kind of realm at every level */
  feudal?: boolean;
  level?: number;
  kind?: string;
  /** holders view */
  entity?: string;
  /** Settlements tab: a thematic list (towns, abbeys, chaumes…) instead of the tenures */
  layer?: Layer;
  filters?: TableFilters;
  /** Table: the column it is sorted by, "-" before it for descending; none is by entry number */
  sort?: string;
}

export const DEFAULT_STATE: State = { view: "map", lang: "en" };
const FILTER_KEYS: [keyof TableFilters, string][] = [["district", "d"], ["realm", "r"], ["section", "t"],
  ["holder", "hd"], ["series", "s"], ["q", "q"]];

export function parseHash(hash: string): State {
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  const q = new URLSearchParams(query);
  const lang = q.get("lang") as Lang;
  const layer = q.get("layer") as Layer;
  const filters: TableFilters = {};
  for (const [key, short] of FILTER_KEYS) {
    const v = q.get(short);
    if (v) filters[key] = v;
  }
  const church = path === "church";   // the former Church & resources tab, now in Settlements
  return {
    view: (VIEWS as readonly string[]).includes(path) ? (path as View) : DEFAULT_STATE.view,
    lang: LANGS.includes(lang) ? lang : browserLang(),
    place: q.get("place") ?? undefined,
    feudal: q.get("h") === "feudal" || undefined,
    level: ["0", "1", "2", "3"].includes(q.get("lvl") ?? "") ? Number(q.get("lvl")) : undefined,
    kind: q.get("kind") || undefined,
    entity: q.get("entity") ?? undefined,
    layer: (LAYERS as readonly string[]).includes(layer) ? layer : church ? "abbeys" : undefined,
    filters: Object.keys(filters).length ? filters : undefined,
    sort: parseSort(q.get("o")),
  };
}

export function toHash(s: State): string {
  const q = new URLSearchParams({ lang: s.lang });
  if (s.place) q.set("place", s.place);
  if (s.feudal) q.set("h", "feudal");
  if (s.level !== undefined) q.set("lvl", String(s.level));
  if (s.kind) q.set("kind", s.kind);
  if (s.entity) q.set("entity", s.entity);
  if (s.layer && s.view === "map") q.set("layer", s.layer);
  for (const [key, short] of FILTER_KEYS) {
    const v = s.filters?.[key];
    if (v) q.set(short, v);
  }
  if (s.sort && s.view === "table") q.set("o", s.sort);
  return `#/${s.view}?${q}`;
}

function parseSort(v: string | null): string | undefined {
  return v && v !== "no" && (SORT_COLUMNS as readonly string[]).includes(v.replace(/^-/, "")) ? v : undefined;
}

function browserLang(): Lang {
  const prefix = (typeof navigator !== "undefined" ? navigator.language : "en").slice(0, 2) as Lang;
  return LANGS.includes(prefix) ? prefix : "en";
}

type Listener = (state: State, previous: State) => void;

export class Store {
  private listeners: Listener[] = [];

  constructor(private current: State) {}

  get state(): State {
    return this.current;
  }

  set(patch: Partial<State>): void {
    const previous = this.current;
    const next = { ...previous, ...patch };
    if (JSON.stringify(next) === JSON.stringify(previous)) return;
    this.current = next;
    for (const listener of this.listeners) listener(next, previous);
  }

  subscribe(listener: Listener): void {
    this.listeners.push(listener);
  }
}
