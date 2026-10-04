// What the map and the panel need to know about a place: its chains up each hierarchy, its
// main tenure and holder, the kind of realm it lies in, and how to draw it in each mode.
import type { Dataset, Holding, Place } from "../data/types";
import { TENURE_COLOURS } from "./colors";

export const DUCHY = "duchy-lorraine";
const TENURE_ORDER = ["domain", "fief", "clergy", "safeguard"];

/** Chains from a place up one hierarchy, nearest first: one per parent of that relation
 *  (a village "en partie" in two prévôtés has two). Territories follow their first parent. */
export function chains(placeId: string, rel: "admin" | "feudal", places: Map<string, Place>): string[][] {
  const start = places.get(placeId)?.parents?.filter((p) => p.rel === rel) ?? [];
  return start.map((first) => {
    const chain = [first.id];
    const seen = new Set([placeId, first.id]);
    let current = places.get(first.id);
    while (current) {
      const up = current.parents?.find((p) => p.rel === rel);
      if (!up || seen.has(up.id) || up.id === DUCHY) break;
      chain.push(up.id);
      seen.add(up.id);
      current = places.get(up.id);
    }
    return chain;
  });
}

/** The division a realm answers to (ressort). */
export function ressortOf(placeId: string, places: Map<string, Place>): string | undefined {
  return places.get(placeId)?.parents?.find((p) => p.rel === "ressort")?.id;
}

/** The holding that gives the place its main tenure (domain first, then fief, clergy, safeguard). */
export function mainHolding(place: Place): Holding | undefined {
  const hold = place.hold ?? [];
  for (const tenure of TENURE_ORDER) {
    const h = hold.find((x) => x.t === tenure);
    if (h) return h;
  }
  return undefined;
}

/** Held only in part ("en partie", "pour la moitié"), or by several holders. */
export function isShared(place: Place): boolean {
  return (place.hold ?? []).some((h) => h.share === "part" || h.share === "1/2" || h.share === "joint")
    || (place.parents ?? []).some((p) => p.share === "part");
}

export interface PlaceStyle {
  fill?: string;
  /** held only in part, or by several holders: hatched */
  shared?: boolean;
}

/** How each located settlement is drawn on the Settlements map: the colour of its main tenure. */
export function placeStyles(data: Dataset): Map<string, PlaceStyle> {
  const styles = new Map<string, PlaceStyle>();
  for (const p of data.places.values()) {
    if (p.kind !== "settlement" || p.lat === undefined) continue;
    const t = mainHolding(p)?.t;
    const fill = t ? TENURE_COLOURS[t] : undefined;
    if (fill) styles.set(p.id, { fill, shared: isShared(p) });
  }
  return styles;
}

/** Counts behind the legend: places per tenure, and those held in part. */
export function counts(data: Dataset): { tenure: Map<string, number>; shared: number } {
  const tenure = new Map<string, number>();
  let shared = 0;
  const bump = <K>(m: Map<K, number>, k: K) => m.set(k, (m.get(k) ?? 0) + 1);
  for (const p of data.places.values()) {
    if (p.kind !== "settlement" || p.lat === undefined) continue;
    const h = mainHolding(p);
    bump(tenure, h?.t ?? "");
    if (h && isShared(p)) shared++;
  }
  return { tenure, shared };
}
