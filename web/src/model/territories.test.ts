import { describe, expect, it } from "vitest";
import type { Dataset } from "../data/types";
import { levelsOf, realmGroup, shownAreas } from "./territories";

const feature = (id: string, hierarchy: string, place_type: string, level: number) => ({
  type: "Feature", properties: { id, hierarchy, place_type, level, settlements: 3, shared: [] }, geometry: null });
const data = { territories: { type: "FeatureCollection", features: [
  feature("duchy-lorraine", "admin", "duchy", 0), feature("bailiwick-nancy", "admin", "bailiwick", 1),
  feature("provostship-nancy", "admin", "provostship", 2), feature("ban-sept", "admin", "ban", 3),
  feature("county-vaudemont", "feudal", "county", 1),
] } } as unknown as Dataset;

describe("territories", () => {
  it("shows one hierarchy at one level, or all levels", () => {
    expect(shownAreas(data, false, 1).map((a) => a.id)).toEqual(["bailiwick-nancy"]);
    expect(shownAreas(data, false, 0).map((a) => a.id)).toEqual(["bailiwick-nancy", "provostship-nancy", "ban-sept"]);
    expect(shownAreas(data, true, 1).map((a) => a.id)).toEqual(["county-vaudemont"]);
    // one kind of realm at every level, whatever the hierarchy
    expect(shownAreas(data, false, 1, "provostship").map((a) => a.id)).toEqual(["provostship-nancy"]);
  });
  it("lists the levels and leaves out the duchy", () => {
    expect(levelsOf(data, false)).toEqual([1, 2, 3]);
    expect(levelsOf(data, true)).toEqual([1]);
  });
  it("groups realms by kind", () => {
    expect(realmGroup("county")).toBe("county");
    expect(realmGroup("fief")).toBe("lordship");
    expect(realmGroup("temporality")).toBe("other");   // church lands: hist_map has no group for them
    expect(realmGroup("provostship")).toBe("office");
    expect(realmGroup("bailiwick")).toBe("office");
    expect(realmGroup("ban")).toBe("other");
  });
});
