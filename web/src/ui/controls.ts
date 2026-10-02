// Header: title, views, colour modes and language. There is no year bar: the book describes 1594.
import type { Dataset, Lang } from "../data/types";
import { LANGS, type StringKey, t } from "../i18n";
import { MODES, type Store, VIEWS } from "../state/store";
import { fill, h } from "./dom";

/** Each language's name in itself, for the switch's accessible labels. */
const LANG_NAMES: Record<Lang, string> = { en: "English", fr: "Français", de: "Deutsch", ja: "日本語" };

export function renderHeader(root: HTMLElement, _data: Dataset, store: Store): void {
  const { lang, mode, view } = store.state;
  fill(root,
    h("div", { class: "topline" },
      h("h1", {}, t("title", lang)),
      VIEWS.length > 1 ? h("nav", { class: "views", "aria-label": t("views", lang) },
        ...VIEWS.map((v) => h("button", { "aria-pressed": String(v === view), onclick: () => store.set({ view: v }) },
          t(`view_${v}` as StringKey, lang)))) : null,
      h("div", { class: "langs", role: "group", "aria-label": t("language", lang) },
        ...LANGS.map((l: Lang) => h("button", { "aria-pressed": String(l === lang), lang: l,
          "aria-label": LANG_NAMES[l], title: LANG_NAMES[l], onclick: () => store.set({ lang: l }) },
        l.toUpperCase())))),
    view === "map" ? h("div", { class: "rightbar" },
      h("nav", { class: "tabs", "aria-label": t("colourBy", lang) },
        ...MODES.map((m) => h("button", { class: "tab", "aria-pressed": String(m === mode),
          title: t(`mode_${m}_title` as StringKey, lang), onclick: () => store.set({ mode: m }) },
        t(`mode_${m}` as StringKey, lang))))) : null,
  );
}
