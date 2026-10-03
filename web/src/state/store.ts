// Application state, mirrored in the URL hash so any view can be linked:
//   #/map?color=tenure&lang=fr&place=saint-avold
//   #/territories?h=feudal&lvl=1     #/holders?entity=abbey-saint-avold     #/church?layer=abbeys
//   #/table?d=provostship-nancy&t=fief&q=chasteau
import type { Lang } from "../data/types";
import { LANGS } from "../i18n";

export const VIEWS = ["map", "territories", "holders", "table", "church", "about"] as const;
export type View = (typeof VIEWS)[number];
/** The map's colour modes. Districts and realms are the Territories view's (an old link falls back to tenure). */
export const MODES = ["tenure", "holder"] as const;
export type Mode = (typeof MODES)[number];
export const LAYERS = ["towns", "churches", "abbeys", "priories", "convents", "commanderies", "chaumes"] as const;
export type Layer = (typeof LAYERS)[number];

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
  mode: Mode;
  lang: Lang;
  place?: string;
  /** holders given the three map colours in holder mode (default: the three most prominent) */
  colours?: string[];
  /** territories view: which hierarchy, and which level (0 = all) */
  feudal?: boolean;
  level?: number;
  /** holders view */
  entity?: string;
  /** church & resources view */
  layer?: Layer;
  filters?: TableFilters;
}

export const DEFAULT_STATE: State = { view: "map", mode: "tenure", lang: "en" };
const FILTER_KEYS: [keyof TableFilters, string][] = [["district", "d"], ["realm", "r"], ["section", "t"],
  ["holder", "hd"], ["series", "s"], ["q", "q"]];

export function parseHash(hash: string): State {
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  const q = new URLSearchParams(query);
  const lang = q.get("lang") as Lang;
  const mode = q.get("color") as Mode;
  const layer = q.get("layer") as Layer;
  const filters: TableFilters = {};
  for (const [key, short] of FILTER_KEYS) {
    const v = q.get(short);
    if (v) filters[key] = v;
  }
  return {
    view: (VIEWS as readonly string[]).includes(path) ? (path as View) : DEFAULT_STATE.view,
    mode: (MODES as readonly string[]).includes(mode) ? mode : DEFAULT_STATE.mode,
    lang: LANGS.includes(lang) ? lang : browserLang(),
    place: q.get("place") ?? undefined,
    colours: q.get("c")?.split(",").filter(Boolean).slice(0, 3) || undefined,
    feudal: q.get("h") === "feudal" || undefined,
    level: ["0", "1", "2", "3"].includes(q.get("lvl") ?? "") ? Number(q.get("lvl")) : undefined,
    entity: q.get("entity") ?? undefined,
    layer: (LAYERS as readonly string[]).includes(layer) ? layer : undefined,
    filters: Object.keys(filters).length ? filters : undefined,
  };
}

export function toHash(s: State): string {
  const q = new URLSearchParams({ color: s.mode, lang: s.lang });
  if (s.place) q.set("place", s.place);
  if (s.colours?.length) q.set("c", s.colours.join(","));
  if (s.feudal) q.set("h", "feudal");
  if (s.level !== undefined) q.set("lvl", String(s.level));
  if (s.entity) q.set("entity", s.entity);
  if (s.layer) q.set("layer", s.layer);
  for (const [key, short] of FILTER_KEYS) {
    const v = s.filters?.[key];
    if (v) q.set(short, v);
  }
  return `#/${s.view}?${q}`;
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
