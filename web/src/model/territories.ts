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

/** The areas of one hierarchy at a level (0 = all levels), or of one kind at every level. */
export function shownAreas(data: Dataset, feudal: boolean, level: number, kind?: string): Area[] {
  if (kind) return areas(data).filter((a) => a.type === kind);
  return areas(data).filter((a) => a.hierarchy === (feudal ? "feudal" : "admin") && (level === 0 || a.level === level));
}

/** The levels a hierarchy has, for the level buttons. */
export function levelsOf(data: Dataset, feudal: boolean): number[] {
  return [...new Set(areas(data).filter((a) => a.hierarchy === (feudal ? "feudal" : "admin")).map((a) => a.level))]
    .sort((a, b) => a - b);
}

/** Kinds of realm, coloured as in hist_map: offices and their like in blue, lordships and fiefs in
 *  orange, counties in green, and the rest (bans, mairies, vals, church lands) in a dark grey. The
 *  book has no principality or marquisate, hist_map's other two groups. */
const GROUPS: Record<string, Exclude<RealmGroup, "other">> = {
  bailiwick: "office", provostship: "office", sub_provostship: "office", castellany: "office", office: "office",
  district: "office", town_district: "office",
  lordship: "lordship", fief: "lordship",
  county: "county",
};
export type RealmGroup = "office" | "county" | "lordship" | "other";
export const GROUP_ORDER: RealmGroup[] = ["office", "county", "lordship", "other"];

export function realmGroup(type: string): RealmGroup {
  return GROUPS[type] ?? "other";
}

/** The place types of one group, for the map's colours. */
export function typesIn(group: Exclude<RealmGroup, "other">): string[] {
  return Object.keys(GROUPS).filter((t) => GROUPS[t] === group);
}

/** The "kind of realm" menu, as in hist_map: administrative divisions, then feudal titles by rank. */
export const KINDS: { group: "administrative" | "feudal"; types: string[] }[] = [
  { group: "administrative", types: ["bailiwick", "provostship", "sub_provostship", "castellany", "office", "district",
    "town_district", "ban", "mayoralty", "val"] },
  { group: "feudal", types: ["county", "lordship", "fief", "temporality"] },
];

/** The level the Territories view shows: the one asked for if the hierarchy has it, else its top level. */
export function currentLevel(data: Dataset, feudal: boolean, level?: number): number {
  const levels = levelsOf(data, feudal);
  return level !== undefined && (level === 0 || levels.includes(level)) ? level : levels[0] ?? 0;
}
