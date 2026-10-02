// Map legend for the colour mode: what each colour stands for, with place counts, the holder
// picker (which three holders get a colour), the hatching key and the kinds of place.
import type { Dataset } from "../data/types";
import { label, name, t } from "../i18n";
import { SHAPE_ORDER, shapeOf, shapeSvg } from "../map/icons";
import { DISTRICT, OTHER, REALM_COLOURS, SERIES, TENURE_COLOURS } from "../model/colors";
import { counts } from "../model/places";
import type { State, Store } from "../state/store";
import { fill, h } from "./dom";

const OTHERS_LISTED = 8;

export function renderLegend(root: HTMLElement, data: Dataset, state: State, store: Store, coloured: string[],
  districts: string[]): void {
  const { lang, mode } = state;
  const c = counts(data);
  const vocab = data.meta.vocab;
  const cap = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
  const swatch = (colour: string, extra = "") => h("span", { class: `swatch ${extra}`, style: `--c:${colour}` });
  const row = (mark: HTMLElement, text: Node | string, count?: number) =>
    h("li", {}, mark, h("span", { class: "label" }, text),
      count !== undefined ? h("span", { class: "count" }, String(count)) : null);
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const entityName = (id: string) => name(data.entities.get(id)?.name, lang, id);
  const select = (id: string) => h("button", { class: "link", "data-place": id, onclick: () => store.set({ place: id }) },
    placeName(id));

  let title = "";
  let rows: HTMLElement[] = [];
  let extra: HTMLElement | null = null;
  if (mode === "tenure") {
    title = t("tenureLegend", lang);
    rows = ["domain", "fief", "clergy"].map((k) => row(swatch(TENURE_COLOURS[k]), cap(label(vocab.tenures[k], lang, k)),
      c.tenure.get(k) ?? 0));
    rows.push(row(swatch(OTHER), t("otherTenure", lang), c.tenure.get("safeguard") ?? 0),
      row(swatch("transparent", "empty"), t("noTenure", lang), c.tenure.get("") ?? 0));
  } else if (mode === "holder") {
    title = t("holderLegend", lang);
    const others = [...c.holder].filter(([id]) => id && !coloured.includes(id)).sort((a, b) => b[1] - a[1]);
    const recolour = (id: string) => () => store.set({ colours: [...coloured.slice(0, 2), id] });
    rows = coloured.map((id, i) => row(swatch(SERIES[i]), entityName(id), c.holder.get(id) ?? 0));
    rows.push(row(swatch(OTHER), t("holderNotNamed", lang), c.holder.get(undefined) ?? 0));
    if (others.length) rows.push(row(swatch(OTHER), `${t("otherHolders", lang)} (${others.length})`,
      others.reduce((s, [, n]) => s + n, 0)));
    extra = others.length ? h("ul", { class: "others" }, ...others.slice(0, OTHERS_LISTED).map(([id, n]) =>
      h("li", {},
        h("button", { class: "pick", title: t("giveColour", lang), "aria-label": `${t("giveColour", lang)}: ${entityName(id!)}`,
          onclick: recolour(id!) }, "●"),
        h("span", { class: "label" }, entityName(id!)), h("span", { class: "count" }, String(n))))) : null;
  } else if (mode === "realm") {
    title = t("realmLegend", lang);
    rows = ["county", "lordship", "temporality"].map((k) => row(swatch(REALM_COLOURS[k]),
      t(`realm_${k}` as "realm_county", lang), c.realm.get(k) ?? 0));
    rows.push(row(swatch("transparent", "empty"), t("notInRealm", lang), c.realm.get(undefined) ?? 0));
  } else {
    title = t("districtLegend", lang);
    rows = [...districts].sort((a, b) => placeName(a).localeCompare(placeName(b), lang))
      .map((id) => row(swatch(DISTRICT), select(id)));
  }

  const settlementShapes = new Set([...data.places.values()].filter((p) => p.kind === "settlement" && p.lat !== undefined)
    .map((p) => shapeOf(p.type)));
  fill(root,
    h("h2", {}, title),
    h("ul", { class: mode === "district" ? "districts" : "" }, ...rows),
    extra,
    mode === "holder" && state.colours?.length
      ? h("button", { class: "link small", onclick: () => store.set({ colours: undefined }) }, t("resetColours", lang))
      : null,
    mode === "tenure" || mode === "holder"
      ? h("ul", { class: "keys" }, row(swatch("#ffffff", "hatched"), t("shared", lang), c.shared)) : null,
    h("h3", {}, t("settlementTypes", lang)),
    h("ul", { class: "shapes" }, ...SHAPE_ORDER.filter((type) => settlementShapes.has(type)).map((type) =>
      h("li", {}, shapeSvg(type), h("span", { class: "label" }, cap(label(vocab.place_types[type], lang, type)))))),
    h("p", { class: "note" }, t("approxAreas", lang)),
    h("p", { class: "note" }, t("blankLand", lang)),
  );
}
