// The Settlements map's legend: what each colour stands for, with place counts, the hatching key and
// the kinds of place.
import type { Dataset } from "../data/types";
import { label, t } from "../i18n";
import { SHAPE_ORDER, shapeOf, shapeSvg } from "../map/icons";
import { OTHER, TENURE_COLOURS } from "../model/colors";
import { counts } from "../model/places";
import type { State } from "../state/store";
import { fill, h } from "./dom";

export function renderLegend(root: HTMLElement, data: Dataset, state: State): void {
  const { lang } = state;
  const c = counts(data);
  const vocab = data.meta.vocab;
  const cap = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
  const swatch = (colour: string, extra = "") => h("span", { class: `swatch ${extra}`, style: `--c:${colour}` });
  const row = (mark: HTMLElement, text: Node | string, count?: number) =>
    h("li", {}, mark, h("span", { class: "label" }, text),
      count !== undefined ? h("span", { class: "count" }, String(count)) : null);
  const rows = ["domain", "fief", "clergy"].map((k) => row(swatch(TENURE_COLOURS[k]), cap(label(vocab.tenures[k], lang, k)),
    c.tenure.get(k) ?? 0));
  rows.push(row(swatch(OTHER), t("otherTenure", lang), c.tenure.get("safeguard") ?? 0),
    row(swatch("transparent", "empty"), t("noTenure", lang), c.tenure.get("") ?? 0));

  const settlementShapes = new Set([...data.places.values()].filter((p) => p.kind === "settlement" && p.lat !== undefined)
    .map((p) => shapeOf(p.type)));
  fill(root,
    h("h2", {}, t("tenureLegend", lang)),
    h("ul", {}, ...rows),
    h("ul", { class: "keys" }, row(swatch("#ffffff", "hatched"), t("shared", lang), c.shared)),
    h("h3", {}, t("settlementTypes", lang)),
    h("ul", { class: "shapes" }, ...SHAPE_ORDER.filter((type) => settlementShapes.has(type)).map((type) =>
      h("li", {}, shapeSvg(type), h("span", { class: "label" }, cap(label(vocab.place_types[type], lang, type)))))),
    h("p", { class: "note" }, t("approxAreas", lang)),
    h("p", { class: "note" }, t("blankLand", lang)),
  );
}
