import { describe, expect, it } from "vitest";
import { DIFFER, FOLLOW, HIEGEL, HIST_MAP, linkedPlaces, namedUnits } from "./compare";

// The section names places by id and entries by number: they must survive a rebuild of the data.
// (web/public/data/, built by make build-data)
const files = import.meta.glob("../../public/data/{places,entries}.json", { eager: true, import: "default" });
const read = (file: string) => {
  const json = files[`../../public/data/${file}`];
  if (!json) throw new Error(`web/public/data/${file} is missing: run make build-data`);
  return json as { id?: string; no?: number | string }[];
};

describe("Alix and Hiegel compared", () => {
  it("links only to places the atlas has", () => {
    const ids = new Set(read("places.json").map((p) => p.id));
    expect(linkedPlaces().filter((id) => !ids.has(id))).toEqual([]);
  });
  it("cites only entries the atlas has", () => {
    const nos = new Set(read("entries.json").map((e) => String(e.no)));
    const cited = [...DIFFER.flatMap((g) => g.rows.flatMap((r) => r.entries)), ...FOLLOW.map((r) => r.entry)];
    expect(cited.filter((no) => !nos.has(String(no)))).toEqual([]);
  });
  it("names every unit of Hiegel's in each language", () => {
    expect(namedUnits().filter((id) => !HIEGEL[id])).toEqual([]);
  });
});

describe("hist_map", () => {
  it("finds the atlas's name in every language", () => {
    for (const text of ["as recorded in the German Bailiwick atlas)", "l'atlas du bailliage d'Allemagne le reprend", "die des Atlas des Deutschen Bellistums",
      "ドイツ・バイイ管区アトラスに収録"]) {
      expect(HIST_MAP.test(text)).toBe(true);
    }
    expect(HIST_MAP.test("Le bailliage d'Allemagne de 1600 à 1632")).toBe(false);   // Hiegel's book
  });
});
