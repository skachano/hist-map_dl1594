import { loadDataset } from "./data/load";
import { label, name, t } from "./i18n";
import { MapView, topDistricts } from "./map/mapView";
import { colouredHolders } from "./model/colors";
import { chains, mainHolding, placeStyles } from "./model/places";
import { parseHash, type State, Store, toHash } from "./state/store";
import "./style.css";
import { renderHeader } from "./ui/controls";
import { fill, h } from "./ui/dom";
import { renderLegend } from "./ui/legend";
import { renderPanel, shareLabel } from "./ui/panel";
import { tooltipPosition } from "./ui/tooltip";

const $ = (id: string) => document.getElementById(id)!;

async function start(): Promise<void> {
  $("status").textContent = t("loading", "en");
  performance.mark("load-start");
  const data = await loadDataset();
  performance.measure("load-data", "load-start");
  const store = new Store(parseHash(location.hash));
  $("status").remove();

  const colours = (state: State) => colouredHolders(data.entities, state.colours?.filter((id) => data.entities.has(id)));
  const districts = topDistricts(data);
  const tooltip = $("tooltip");
  const vocab = data.meta.vocab;

  const map = new MapView($("map"), data, {
    onHover(placeId, point) {
      tooltip.hidden = !placeId;
      if (!placeId) return;
      const { lang, mode } = store.state;
      const p = data.places.get(placeId);
      if (!p) return;
      const placeName = (id: string) => name(data.places.get(id)?.name, lang, id);
      const lines: (HTMLElement | null)[] = [
        h("div", { class: "muted" }, label(vocab.place_types[p.type], lang, p.type)),
      ];
      const held = mainHolding(p);
      if (mode === "tenure" || mode === "holder") {
        lines.push(h("div", {}, held
          ? label(vocab.tenures[held.t], lang, held.t)
            + (held.h ? ` · ${name(data.entities.get(held.h)?.name, lang, held.h)}`
              : held.t !== "domain" ? ` · ${t("holderNotNamed", lang)}` : "")
            + (held.share ? ` (${shareLabel(held.share, lang)})` : "")
          : t("noTenure", lang)));
      }
      const chain = mode === "realm" ? chains(p.id, "feudal", data.places)[0] : chains(p.id, "admin", data.places)[0];
      if (chain?.length) lines.push(h("div", { class: "muted" }, [...chain].reverse().map(placeName).join(" › ")));
      else if (mode === "realm") lines.push(h("div", { class: "muted" }, t("notInRealm", lang)));
      fill(tooltip, h("strong", {}, placeName(placeId)), ...lines);
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

  let returnFocus: HTMLElement | null = null;
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && store.state.place) store.set({ place: undefined });
  });

  const render = (state: State, previous?: State) => {
    const started = performance.now();
    const focusedBefore = document.activeElement as HTMLElement | null; // views re-render below
    const coloured = colours(state);
    document.documentElement.lang = state.lang;
    document.title = t("title", state.lang);
    document.body.dataset.view = state.view;
    document.body.classList.toggle("panel-open", !!state.place);
    renderHeader($("header"), data, store);
    const shownDistricts = state.mode === "district" ? districts : [];
    renderLegend($("legend"), data, state, store, coloured, districts);
    renderPanel($("panel"), data, state, store);
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
    const names = new Map(shownDistricts.map((id) => [id, name(data.places.get(id)?.name, state.lang, id)]));
    void map.render(placeStyles(data, state.mode, coloured), shownDistricts, names, state.place);
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
