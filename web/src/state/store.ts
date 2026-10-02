// Application state, mirrored in the URL hash so any view can be linked:
//   #/map?color=tenure&lang=fr&place=saint-avold
import type { Lang } from "../data/types";
import { LANGS } from "../i18n";

export const VIEWS = ["map"] as const;
export type View = (typeof VIEWS)[number];
export const MODES = ["tenure", "holder", "district", "realm"] as const;
export type Mode = (typeof MODES)[number];

export interface State {
  view: View;
  mode: Mode;
  lang: Lang;
  place?: string;
  /** holders given the three map colours in holder mode (default: the three most prominent) */
  colours?: string[];
}

export const DEFAULT_STATE: State = { view: "map", mode: "tenure", lang: "en" };

export function parseHash(hash: string): State {
  const [path, query = ""] = hash.replace(/^#\/?/, "").split("?");
  const q = new URLSearchParams(query);
  const lang = q.get("lang") as Lang;
  const mode = q.get("color") as Mode;
  return {
    view: (VIEWS as readonly string[]).includes(path) ? (path as View) : DEFAULT_STATE.view,
    mode: (MODES as readonly string[]).includes(mode) ? mode : DEFAULT_STATE.mode,
    lang: LANGS.includes(lang) ? lang : browserLang(),
    place: q.get("place") ?? undefined,
    colours: q.get("c")?.split(",").filter(Boolean).slice(0, 3) || undefined,
  };
}

export function toHash(s: State): string {
  const q = new URLSearchParams({ color: s.mode, lang: s.lang });
  if (s.place) q.set("place", s.place);
  if (s.colours?.length) q.set("c", s.colours.join(","));
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
