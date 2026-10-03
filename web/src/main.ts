import { loadDataset } from "./data/load";
import { label, name, t } from "./i18n";
import { type AreaLayer, MapView } from "./map/mapView";
import { SERIES } from "./model/colors";
import { chains, mainHolding, type PlaceStyle, placeStyles } from "./model/places";
import { currentLevel, shownAreas } from "./model/territories";
import { parseHash, type State, Store, toHash } from "./state/store";
import "./style.css";
import { renderHeader } from "./ui/controls";
import { fill, h } from "./ui/dom";
import { renderAbout } from "./ui/about";
import { renderLegend } from "./ui/legend";
import { setMapFocus } from "./ui/navigate";
import { renderTable } from "./ui/pages";
import { childrenOf, renderPanel, shareLabel } from "./ui/panel";
import { layerEntries, renderChurchView, renderHoldersView, renderTerritoriesView } from "./ui/sideViews";
import { tooltipPosition } from "./ui/tooltip";

const $ = (id: string) => document.getElementById(id)!;

async function start(): Promise<void> {
  $("status").textContent = t("loading", "en");
  performance.mark("load-start");
  const data = await loadDataset();
  performance.measure("load-data", "load-start");
  const store = new Store(parseHash(location.hash));
  $("status").remove();

  const tooltip = $("tooltip");
  const vocab = data.meta.vocab;

  const map = new MapView($("map"), data, {
    onHover(placeId, point) {
      tooltip.hidden = !placeId;
      if (!placeId) return;
      const { lang } = store.state;
      const p = data.places.get(placeId);
      if (!p) return;
      const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
      if (p.kind === "territory") {
        // An area of the Territories view: its kind and how many places it has.
        const members = childrenOf(data).get(p.id) ?? [];
        const settlements = members.filter((m) => data.places.get(m.id)?.kind === "settlement").length;
        fill(tooltip, h("strong", {}, placeName(placeId)),
          h("div", { class: "muted" }, label(vocab.territory_types[p.type], lang, p.type)),
          h("div", {}, `${settlements} ${t("places", lang)}`));
      } else {
      const lines: (HTMLElement | null)[] = [
        h("div", { class: "muted" }, label(vocab.place_types[p.type], lang, p.type)),
      ];
      const held = mainHolding(p);
      lines.push(h("div", {}, held
        ? label(vocab.tenures[held.t], lang, held.t)
          + (held.h ? ` · ${name(data.entities.get(held.h)?.name, lang, held.h)}`
            : held.t !== "domain" ? ` · ${t("holderNotNamed", lang)}` : "")
          + (held.share ? ` (${shareLabel(held.share, lang)})` : "")
        : t("noTenure", lang)));
      const chain = chains(p.id, "admin", data.places)[0];
      if (chain?.length) lines.push(h("div", { class: "muted" }, [...chain].reverse().map(placeName).join(" › ")));
      fill(tooltip, h("strong", {}, placeName(placeId)), ...lines);
      }
      const area = tooltip.offsetParent as HTMLElement | null; // the map's stage
      const pos = tooltipPosition(point, { width: tooltip.offsetWidth, height: tooltip.offsetHeight },
        { width: area?.clientWidth ?? window.innerWidth, height: area?.clientHeight ?? window.innerHeight });
      tooltip.style.transform = `translate(${pos.x}px, ${pos.y}px)`;
    },
    onSelect(placeId) {
      store.set({ place: placeId });
    },
  });
  // Development only: lets end-to-end tests point at a place on the map.
  if (import.meta.env.DEV) (window as unknown as { __map: unknown }).__map = map.map;
  setMapFocus(map);

  let returnFocus: HTMLElement | null = null;
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && store.state.place) store.set({ place: undefined });
  });

  /** What the map draws in each view: the places' colours and the territory areas. */
  const mapLayers = (state: State): { styles: Map<string, PlaceStyle>; areas: AreaLayer } => {
    const none: AreaLayer = { ids: [], feudal: false, interactive: false };
    if (state.view === "territories") {
      const feudal = !!state.feudal;
      const ids = shownAreas(data, feudal, currentLevel(data, feudal, state.level), state.kind).map((a) => a.id);
      return { styles: new Map(), areas: { ids, feudal, interactive: true } };
    }
    if (state.view === "holders") {
      const entity = state.entity && data.entities.has(state.entity) ? state.entity
        : [...data.entities.values()].sort((a, b) => a.rank - b.rank)[0]?.id;
      const styles = new Map<string, PlaceStyle>();
      for (const p of data.places.values()) {
        const held = p.hold?.filter((x) => x.h === entity) ?? [];
        if (p.kind === "settlement" && held.length) {
          styles.set(p.id, { fill: SERIES[0], shared: held.some((x) => !!x.share) || p.hold!.length > held.length });
        }
      }
      const realms = [...data.places.values()].filter((p) => p.kind === "territory" && entity && p.holder?.includes(entity));
      return { styles, areas: { ids: realms.map((p) => p.id), feudal: true, interactive: false } };
    }
    if (state.view === "church") {
      const styles = new Map<string, PlaceStyle>();
      const colour = state.layer === "towns" ? SERIES[0] : SERIES[2];
      for (const e of layerEntries(data, state.layer ?? "abbeys")) if (e.place) styles.set(e.place, { fill: colour });
      return { styles, areas: none };
    }
    return { styles: placeStyles(data), areas: none };
  };

  const render = (state: State, previous?: State) => {
    const started = performance.now();
    const focusedBefore = document.activeElement as HTMLElement | null; // views re-render below
    document.documentElement.lang = state.lang;
    document.title = t("title", state.lang);
    document.body.dataset.view = state.view;
    document.body.classList.toggle("panel-open", !!state.place);
    renderHeader($("header"), data, store);
    const { styles, areas } = mapLayers(state);
    const onMap = state.view !== "table" && state.view !== "about";
    const side = $("side"), page = $("page"), legend = $("legend");
    legend.hidden = state.view !== "map";
    if (state.view === "map") renderLegend(legend, data, state);
    side.hidden = !["territories", "holders", "church"].includes(state.view);
    if (state.view === "territories") renderTerritoriesView(side, data, state, store);
    else if (state.view === "holders") renderHoldersView(side, data, state, store);
    else if (state.view === "church") renderChurchView(side, data, state, store);
    else fill(side);
    page.hidden = onMap;
    if (state.view === "table") renderTable(page, data, state, store);
    else if (state.view === "about") renderAbout(page, data, state.lang);
    else fill(page);
    renderPanel($("panel"), data, onMap ? state : { ...state, place: undefined }, store);
    if (!onMap) tooltip.hidden = true;
    // Keyboard and screen-reader users land in the panel when it opens and return when it closes.
    if (previous && state.place !== previous.place) {
      if (state.place) {
        if (!previous.place) returnFocus = focusedBefore;
        ($("panel").querySelector("h2") as HTMLElement | null)?.focus({ preventScroll: true });
      } else {
        const target = returnFocus?.isConnected && returnFocus !== document.body ? returnFocus
          : document.querySelector<HTMLElement>(`[data-place="${CSS.escape(previous.place ?? "")}"]`);
        target?.focus({ preventScroll: true });
        returnFocus = null;
      }
    }
    const names = new Map(areas.ids.map((id) => [id, name(data.places.get(id)?.name, state.lang, id)]));
    if (onMap) void map.render(styles, areas, names, state.place);
    history.replaceState(null, "", toHash(state));
    performance.measure(`render:${state.view}`, { start: started }); // read by end-to-end performance tests
  };
  store.subscribe(render);
  window.addEventListener("hashchange", () => store.set(parseHash(location.hash)));
  render(store.state);
}

start().catch((error) => {
  console.error(error);
  $("status").textContent = t("loadError", "en");
});
