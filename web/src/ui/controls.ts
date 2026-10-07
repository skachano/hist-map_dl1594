// Header: title, views, language, and on the Settlements tab what its map shows. There is no year bar: the book describes 1594.
import type { Dataset, Lang } from "../data/types";
import { LANGS, type StringKey, t } from "../i18n";
import { LAYERS, type Layer, type Store, VIEWS } from "../state/store";
import { fill, h } from "./dom";

/** Each language's name in itself, for the switch's accessible labels. */
const LANG_NAMES: Record<Lang, string> = { en: "English", fr: "Français", de: "Deutsch", ja: "日本語" };

export function renderHeader(root: HTMLElement, _data: Dataset, store: Store): void {
  const { lang, view } = store.state;
  // The header is rebuilt on every change; the rows that scroll sideways on phones keep their place.
  const scrolled = [".views", ".modes"].map((s) => root.querySelector(s)?.scrollLeft ?? 0);
  fill(root,
    view !== "table" ? h("button", { class: "skip", onclick: () => store.set({ view: "table" }) },
      t("skipToTable", lang)) : null,
    h("div", { class: "topline" },
      h("h1", {}, t("title", lang)),
      VIEWS.length > 1 ? h("nav", { class: "views", "aria-label": t("views", lang) },
        ...VIEWS.map((v) => h("button", { "aria-pressed": String(v === view), onclick: () => store.set({ view: v }) },
          t(`view_${v}` as StringKey, lang)))) : null,
      h("div", { class: "langs", role: "group", "aria-label": t("language", lang) },
        ...LANGS.map((l: Lang) => h("button", { "aria-pressed": String(l === lang), lang: l,
          "aria-label": LANG_NAMES[l], title: LANG_NAMES[l], onclick: () => store.set({ lang: l }) },
        l.toUpperCase())))),
    // Settlements: the tenures (with the legend) or one thematic layer (with its list)
    view === "map" ? h("div", { class: "modes", role: "group", "aria-label": t("settlementsShow", lang) },
      ...([undefined, ...LAYERS] as (Layer | undefined)[]).map((l) => h("button", {
        "aria-pressed": String(l === store.state.layer), onclick: () => store.set({ layer: l }) },
      t(`layer_${l ?? "tenures"}` as StringKey, lang)))) : null,
  );
  [".views", ".modes"].forEach((s, i) => { const el = root.querySelector(s); if (el) el.scrollLeft = scrolled[i]; });
}
