import { describe, expect, it } from "vitest";
import { parseHash, toHash } from "./store";

describe("URL state", () => {
  it("round-trips the map", () => {
    const s = parseHash("#/map?color=realm&lang=fr&place=saint-avold&c=a,b");
    expect(s).toMatchObject({ view: "map", mode: "realm", lang: "fr", place: "saint-avold", colours: ["a", "b"] });
    expect(parseHash(toHash(s))).toEqual(s);
  });
  it("round-trips the other views", () => {
    for (const hash of ["#/territories?color=tenure&lang=de&h=feudal&lvl=0", "#/holders?color=tenure&lang=en&entity=x",
      "#/church?color=tenure&lang=ja&layer=abbeys", "#/table?color=tenure&lang=fr&d=provostship-nancy&t=fief&q=chasteau"]) {
      expect(toHash(parseHash(hash))).toBe(hash);
    }
  });
  it("falls back to defaults", () => {
    const s = parseHash("#/nowhere?color=rainbow&lang=xx&lvl=9&layer=x");
    expect(s.view).toBe("map");
    expect(s.mode).toBe("tenure");
    expect(s.level).toBeUndefined();
    expect(s.layer).toBeUndefined();
  });
  it("has no year", () => {
    expect(toHash(parseHash(""))).not.toContain("year");
  });
});
