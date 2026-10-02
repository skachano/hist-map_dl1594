import { describe, expect, it } from "vitest";
import { parseHash, toHash } from "./store";

describe("URL state", () => {
  it("round-trips", () => {
    const s = parseHash("#/map?color=realm&lang=fr&place=saint-avold&c=a,b");
    expect(s).toEqual({ view: "map", mode: "realm", lang: "fr", place: "saint-avold", colours: ["a", "b"] });
    expect(parseHash(toHash(s))).toEqual(s);
  });
  it("falls back to defaults", () => {
    const s = parseHash("#/nowhere?color=rainbow&lang=xx");
    expect(s.view).toBe("map");
    expect(s.mode).toBe("tenure");
    expect(["en", "fr", "de", "ja"]).toContain(s.lang);
  });
  it("has no year", () => {
    expect(toHash(parseHash(""))).not.toContain("year");
  });
});
