// Full pages: the Table of the Dénombrement's entries, in the book's order or sorted by a column,
// with filters and a CSV export. This is where the book is read in order, and the keyboard's way to every fact.
import type { Dataset, Entry } from "../data/types";
import { label, name, t } from "../i18n";
import { shapeSvg } from "../map/icons";
import { OTHER, TENURE_COLOURS } from "../model/colors";
import { DUCHY } from "../model/places";
import { SORT_COLUMNS, type SortColumn, type State, type Store, type TableFilters } from "../state/store";
import { fill, h } from "./dom";
import { openPlace, showOnMap } from "./navigate";
import { childrenOf, indexIdentification } from "./panel";

/** Who holds what an entry lists: the named holders, else the duke for domain and safeguards. */
export function entryHolders(e: Entry): string[] {
  if (e.holders?.length) return e.holders;
  return e.section === "domain" || e.section === "safeguard" ? [DUCHY] : [];
}

/** A territory and every territory below it (through the same kind of link). */
function within(data: Dataset, id: string): Set<string> {
  const out = new Set([id]);
  const queue = [id];
  const children = childrenOf(data);
  while (queue.length) {
    for (const c of children.get(queue.pop()!) ?? []) {
      if (data.places.get(c.id)?.kind === "territory" && !out.has(c.id)) {
        out.add(c.id);
        queue.push(c.id);
      }
    }
  }
  return out;
}

export function filterEntries(data: Dataset, f: TableFilters = {}): Entry[] {
  const districts = f.district ? within(data, f.district) : undefined;
  const words = (f.q ?? "").toLowerCase().split(/\s+/).filter(Boolean);
  return data.entries.filter((e) =>
    (!districts || (!!e.district && districts.has(e.district)))
    && (!f.realm || e.realm === f.realm)
    && (!f.section || e.section === f.section)
    && (!f.holder || entryHolders(e).includes(f.holder))
    && (!f.series || (e.series ?? "main") === f.series)
    && words.every((w) => `${e.text} ${e.name}`.toLowerCase().includes(w)));
}

/** `sort` as in the URL ("place", "-place"); by entry number, the book's order, when none. Empty
 * values go last either way, and ties keep the book's order. */
export function sortEntries(rows: Entry[], sort: string | undefined, value: (e: Entry, col: SortColumn) => string,
  lang: string): Entry[] {
  const desc = !!sort?.startsWith("-");
  const col = (sort?.replace(/^-/, "") || "no") as SortColumn;
  if (col === "no") return desc ? [...rows].reverse() : rows;
  const collator = new Intl.Collator(lang, { numeric: true, sensitivity: "base" });
  const keyed = rows.map((e, i) => [e, value(e, col), i] as const);
  keyed.sort(([, x, i], [, y, j]) =>
    (!x || !y ? Number(!x) - Number(!y) : (desc ? -1 : 1) * collator.compare(x, y)) || i - j);
  return keyed.map(([e]) => e);
}

function csv(rows: string[][]): string {
  return rows.map((r) => r.map((v) => /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v).join(",")).join("\n");
}

export function renderTable(root: HTMLElement, data: Dataset, state: State, store: Store): void {
  const { lang } = state;
  const f = state.filters ?? {};
  const vocab = data.meta.vocab;
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const setFilter = (key: keyof TableFilters, value: string) => {
    const next = { ...f, [key]: value || undefined };
    for (const k of Object.keys(next) as (keyof TableFilters)[]) if (!next[k]) delete next[k];
    store.set({ filters: Object.keys(next).length ? next : undefined });
  };
  const select = (key: keyof TableFilters, title: string, options: [string, string][]) =>
    h("label", { class: "kind" }, title,
      h("select", { onchange: (e: Event) => setFilter(key, (e.target as HTMLSelectElement).value) },
        h("option", { value: "" }, t("all", lang)),
        ...options.map(([v, text]) => h("option", { value: v, selected: f[key] === v }, text))));
  const territories = (h_: "admin" | "feudal") => [...data.places.values()]
    .filter((p) => p.kind === "territory" && p.h === h_ && p.id !== DUCHY)
    .map((p) => [p.id, placeName(p.id)] as [string, string]).sort((a, b) => a[1].localeCompare(b[1], lang));
  // Every place the entry names: the one it is matched to, then those the index adds.
  const placesOf = (e: Entry) => [e.place, ...(e.also ?? [])].filter((id): id is string => !!id);
  const settlement = (e: Entry) => {
    const p = e.place ? data.places.get(e.place) : undefined;
    return p?.kind === "settlement" ? p : undefined;
  };
  const typeLabel = (e: Entry) => {
    const p = settlement(e);
    const text = p ? label(vocab.place_types[p.type], lang, p.type) : "";
    return text.charAt(0).toUpperCase() + text.slice(1);   // as in the legend
  };
  const tenure = (e: Entry) => e.series
    ? label(vocab.series[e.series], lang, e.series) : label(vocab.sections[e.section ?? ""], lang, e.section ?? "");
  const onPage = (page?: string) => page ? ` (${t("pages", lang)} ${page})` : "";
  // Thierry Alix's entry, and the editor's index lines for it, each with its page.
  const alix = (e: Entry) => `${e.text}${onPage(e.page)}`;
  const index = (e: Entry) => (e.ix ?? []).map((x) => {
    const p = x.place ? data.places.get(x.place) : undefined;
    const where = p ? indexIdentification(p, lang) : "";
    return `${x.s}${where ? `, ${where}` : ""}${onPage(x.p)}${x.np ? ` [${t("numberNotPrinted", lang)}]` : ""}`;
  }).join("; ");
  const sortValue = (e: Entry, col: SortColumn) => ({
    type: typeLabel, no: (x: Entry) => String(x.no), place: (x: Entry) => placesOf(x).map(placeName).join(", "),
    district: (x: Entry) => x.district ? placeName(x.district) : "", tenure, alix: (x: Entry) => x.text, index,
  })[col](e);
  const rows = sortEntries(filterEntries(data, f), state.sort, sortValue, lang);
  const cells = (e: Entry) => [
    typeLabel(e), String(e.no), placesOf(e).map(placeName).join(", "), e.district ? placeName(e.district) : "",
    tenure(e), alix(e), index(e),
  ];
  const head = [t("type", lang), t("entry", lang), t("place", lang), t("district", lang), t("tenure", lang),
    t("alixEntry", lang), t("editorsIndex", lang)];
  const icon = (e: Entry) => {
    const p = settlement(e);
    if (!p) return "";
    return h("span", { class: "type-icon", title: typeLabel(e) },
      shapeSvg(p.type, p.tenure ? TENURE_COLOURS[p.tenure] ?? OTHER : "#ffffff"), h("span", { class: "visually-hidden" }, typeLabel(e)));
  };
  const exportCsv = () => {
    const blob = new Blob([csv([head, ...rows.map(cells)])], { type: "text/csv;charset=utf-8" });
    const a = h("a", { href: URL.createObjectURL(blob), download: "denombrement-1594.csv" });
    a.click();
    URL.revokeObjectURL(a.href);
  };
  // Each column header sorts by it; again, the other way. The entry number is the default order.
  const [sortCol, sortDesc] = [(state.sort?.replace(/^-/, "") || "no") as SortColumn, !!state.sort?.startsWith("-")];
  const sortHeader = (col: SortColumn, i: number) => {
    const active = col === sortCol;
    const next = active && !sortDesc ? `-${col}` : col;
    return h("th", { scope: "col", class: "sortable", "aria-sort": active ? (sortDesc ? "descending" : "ascending") : undefined },
      h("button", { class: "sort", onclick: () => store.set({ sort: next === "no" ? undefined : next }) },
        i ? head[i] : h("span", { class: "visually-hidden" }, head[i]),
        h("span", { class: "arrow", "aria-hidden": "true" })));
  };
  const link = (id: string, onclick: () => void) => h("button", { class: "link", "data-place": id, onclick }, placeName(id));
  fill(root,
    h("div", { class: "toolbar" },
      h("h2", {}, t("view_table", lang)),
      select("district", t("district", lang), territories("admin")),
      select("realm", t("realm", lang), territories("feudal")),
      select("section", t("section", lang), Object.keys(vocab.sections).map((k) => [k, label(vocab.sections[k], lang, k)])),
      select("holder", t("holderLegend", lang), [...data.entities.values()].sort((a, b) => a.rank - b.rank)
        .map((e) => [e.id, name(e.name, lang, e.id)])),
      select("series", t("list", lang), Object.keys(vocab.series).map((k) => [k, label(vocab.series[k], lang, k)])),
      h("label", { class: "kind" }, t("search", lang),
        h("input", { type: "search", value: f.q ?? "", onchange: (e: Event) => setFilter("q", (e.target as HTMLInputElement).value) })),
      h("span", { class: "muted" }, `${rows.length} ${t("entriesShown", lang)}`),
      h("button", { onclick: exportCsv }, t("exportCsv", lang))),
    h("div", { class: "table-wrap" },
      h("table", { class: "matrix" },
        h("thead", {}, h("tr", {}, ...SORT_COLUMNS.map(sortHeader))),
        h("tbody", {}, ...rows.map((e) => h("tr", {},
          h("td", { class: "type-cell" }, icon(e)),
          h("th", { scope: "row" }, String(e.no)),
          h("td", {}, ...placesOf(e).flatMap((id, i) => [i ? ", " : "", link(id, () => showOnMap(store, id))])),
          h("td", {}, e.district ? link(e.district, () => openPlace(store, data, e.district!)) : ""),
          h("td", {}, tenure(e)),
          h("td", {}, alix(e)),
          h("td", {}, index(e))))))),
  );
}
