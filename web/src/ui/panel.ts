// Place panel: names in four languages and the book's spellings, the editor's identification,
// the chains up both hierarchies (district and realm), tenure and holders, and every entry of the
// Dénombrement that names the place, with its number, text and page. A territory also shows its
// holder, the division it answers to, its counterpart on the same land, and its members.
import type { Dataset, Entry, Place } from "../data/types";
import { label, LANGS, name, t } from "../i18n";
import { chains, ressortOf } from "../model/places";
import type { State, Store } from "../state/store";
import { fill, h } from "./dom";

const childrenCache = new WeakMap<Dataset, Map<string, { id: string; rel: string }[]>>();

/** Direct members of each territory (settlements and territories), through admin or feudal links. */
export function childrenOf(data: Dataset): Map<string, { id: string; rel: string }[]> {
  let children = childrenCache.get(data);
  if (!children) {
    children = new Map();
    for (const p of data.places.values()) {
      for (const parent of p.parents ?? []) {
        if (parent.rel === "ressort") continue;
        const list = children.get(parent.id) ?? [];
        list.push({ id: p.id, rel: parent.rel });
        children.set(parent.id, list);
      }
    }
    childrenCache.set(data, children);
  }
  return children;
}

/** "part" -> "in part", "1/2" -> "half", "joint" -> "jointly". */
export function shareLabel(share: string, lang: State["lang"]): string {
  if (share === "part") return t("sharePart", lang);
  if (share === "joint") return t("shareJoint", lang);
  if (share === "1/2") return t("shareHalf", lang);
  return share;
}

export function renderPanel(root: HTMLElement, data: Dataset, state: State, store: Store): void {
  const place = state.place ? data.places.get(state.place) : undefined;
  root.hidden = !place;
  if (!place) return fill(root);
  const { lang } = state;
  const vocab = data.meta.vocab;
  const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
  const entityName = (id: string) => name(data.entities.get(id)?.name, lang, id);
  const link = (id: string) => h("button", { class: "link", "data-place": id, onclick: () => store.set({ place: id }) },
    placeName(id));
  const typeLabels = (p: Place) => {
    const labels = (p.kind === "territory" ? vocab.territory_types : vocab.place_types)[p.type];
    return LANGS.filter((l) => labels?.[l]).map((l) => label(labels, l, p.type)).join(" · ");
  };
  // A chain shown from the top down: bailliage › prévôté › ban.
  const crumbs = (chain: string[]) => h("dd", { class: "crumbs" }, ...[...chain].reverse().map(link));

  const admin = chains(place.id, "admin", data.places);
  const feudal = chains(place.id, "feudal", data.places);
  const isTerritory = place.kind === "territory";
  const ressort = isTerritory ? ressortOf(place.id, data.places) : undefined;
  const index = place.index ?? {};
  const where = [
    index.kind,
    index.commune ? `${t("commune", lang)} ${index.commune}` : "",
    index.canton ? `${t("canton", lang)} ${index.canton}` : "",
    index.dept ?? "",
  ].filter(Boolean).join(", ");
  const location = place.kind === "settlement"
    ? place.lat === undefined ? t("unlocated", lang)
      : place.approx ? t("approximate", lang) : place.geo === "low" ? t("lowConfidence", lang) : ""
    : "";

  const entries = (place.entries ?? []).map((no) => data.entryByNo.get(no)).filter((e): e is Entry => !!e);
  const entryItem = (e: Entry) => h("li", {},
    h("span", { class: "no" }, `${t("entry", lang)} ${e.no}`), " ",
    h("q", {}, e.text),
    h("div", { class: "muted" }, [
      e.series ? label(vocab.series[e.series], lang, e.series) : e.section ? label(vocab.sections[e.section], lang, e.section) : "",
      e.district ? placeName(e.district) : "",
      e.realm ? placeName(e.realm) : "",
      e.page ? `${t("pages", lang)} ${e.page}` : "",
    ].filter(Boolean).join(" · ")));

  const members = isTerritory ? childrenOf(data).get(place.id) ?? [] : [];
  const memberTerritories = members.filter((m) => data.places.get(m.id)?.kind === "territory").map((m) => m.id);
  const memberSettlements = members.filter((m) => data.places.get(m.id)?.kind === "settlement").map((m) => m.id);
  // The book's order: by the first entry that names the member; places the book never numbers come last.
  const firstNo = (id: string) => Math.min(Infinity, ...(data.places.get(id)?.entries ?? []).map((n) => parseInt(String(n), 10)));
  const bookOrder = (a: string, b: string) => firstNo(a) - firstNo(b) || placeName(a).localeCompare(placeName(b), lang);
  const member = (id: string) => h("li", {},
    Number.isFinite(firstNo(id)) ? h("span", { class: "no" }, `${firstNo(id)} `) : "", link(id));

  fill(root,
    h("button", { class: "close", "aria-label": t("close", lang), onclick: () => store.set({ place: undefined }) }, "×"),
    h("h2", { tabindex: "-1" }, placeName(place.id)),
    h("dl", {},
      h("dt", {}, t("names", lang)),
      h("dd", {}, `FR ${place.name.fr ?? "—"} · DE ${place.name.de ?? "—"} · EN ${place.name.en ?? "—"}`
        + (place.name.ja ? ` · JA ${place.name.ja}` : "")),
      place.variants?.length ? h("dt", {}, t("spellings", lang)) : null,
      place.variants?.length ? h("dd", { class: "muted" }, place.variants.join(", ")) : null,
      h("dt", {}, t("type", lang)),
      h("dd", {}, typeLabels(place)),
      where || place.lost ? h("dt", {}, t("index", lang)) : null,
      where ? h("dd", {}, where) : null,
      place.lost ? h("dd", { class: "muted" }, t("lostPlace", lang)) : null,
      admin.length ? h("dt", {}, t("district", lang)) : null,
      ...admin.map(crumbs),
      feudal.length ? h("dt", {}, t("realm", lang)) : null,
      ...feudal.map(crumbs),
      ressort ? h("dt", {}, t("answersTo", lang)) : null,
      ressort ? h("dd", {}, link(ressort)) : null,
      place.counterpart ? h("dt", {}, t("sameLand", lang)) : null,
      place.counterpart ? h("dd", {}, link(place.counterpart),
        place.basis ? h("span", { class: "muted" }, ` (${label(vocab.counterpart_bases[place.basis], lang, place.basis)})`) : "")
        : null,
      place.holder?.length ? h("dt", {}, t("heldBy", lang)) : null,
      place.holder?.length ? h("dd", {}, place.holder.map(entityName).join(", ")) : null,
    ),
    location ? h("p", { class: "muted" }, location) : null,
    place.hold?.length ? h("h3", {}, t("tenure", lang)) : null,
    place.hold?.length ? h("ul", { class: "holdings" }, ...place.hold.map((x) => h("li", {},
      h("strong", {}, label(vocab.tenures[x.t], lang, x.t)),
      x.h ? ` · ${entityName(x.h)}` : x.t === "fief" || x.t === "clergy" ? ` · ${t("holderNotNamed", lang)}` : "",
      x.share ? ` (${shareLabel(x.share, lang)})` : "",
      h("span", { class: "muted" }, ` · ${t("entry", lang)} ${x.e.join(", ")}`)))) : null,
    entries.length ? h("h3", {}, t("entries", lang)) : null,
    entries.length ? h("ul", { class: "entries" }, ...entries.map(entryItem)) : null,
    memberTerritories.length ? h("h3", {}, `${t("subTerritories", lang)} (${memberTerritories.length})`) : null,
    memberTerritories.length ? h("ul", { class: "members" }, ...memberTerritories.sort(bookOrder).map(member))
      : null,
    memberSettlements.length ? h("h3", {}, `${t("members", lang)} (${memberSettlements.length})`) : null,
    memberSettlements.length ? h("ul", { class: "members cols" },
      ...memberSettlements.sort(bookOrder).map(member)) : null,
    h("p", { class: "muted" }, `${t("source", lang)}: Alix, Dénombrement (1594), éd. 1870`
      + (place.pages ? `, ${t("pages", lang)} ${place.pages}` : "")),
  );
}
