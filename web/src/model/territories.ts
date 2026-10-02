// The Territories view: which areas a hierarchy shows at a level, and what each contains.
import type { Dataset } from "../data/types";

export interface Area {
  id: string;
  hierarchy: "admin" | "feudal";
  type: string;
  level: number;
  settlements: number;
  shared: string[];
}

const cache = new WeakMap<Dataset, Area[]>();

/** Every territory with an area (territories.geojson), duchy excluded. */
export function areas(data: Dataset): Area[] {
  let list = cache.get(data);
  if (!list) {
    list = data.territories.features.map((f) => {
      const p = f.properties ?? {};
      return { id: String(p.id), hierarchy: p.hierarchy, type: p.place_type, level: Number(p.level),
        settlements: Number(p.settlements), shared: (p.shared ?? []) as string[] };
    }).filter((a) => a.level > 0);
    cache.set(data, list);
  }
  return list;
}

/** The areas of one hierarchy at a level (0 = all levels). */
export function shownAreas(data: Dataset, feudal: boolean, level: number): Area[] {
  return areas(data).filter((a) => a.hierarchy === (feudal ? "feudal" : "admin") && (level === 0 || a.level === level));
}

/** The levels a hierarchy has, for the level buttons. */
export function levelsOf(data: Dataset, feudal: boolean): number[] {
  return [...new Set(areas(data).filter((a) => a.hierarchy === (feudal ? "feudal" : "admin")).map((a) => a.level))]
    .sort((a, b) => a - b);
}

/** Group of a realm's type for its colour: county, church lands, else lordship. */
export function realmGroup(type: string): "county" | "temporality" | "lordship" {
  return type === "county" || type === "temporality" ? type : "lordship";
}

/** The level the Territories view shows: the one asked for if the hierarchy has it, else its top level. */
export function currentLevel(data: Dataset, feudal: boolean, level?: number): number {
  const levels = levelsOf(data, feudal);
  return level !== undefined && (level === 0 || levels.includes(level)) ? level : levels[0] ?? 0;
}
