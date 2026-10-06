import { describe, expect, it } from "vitest";
import { parseHash, toHash } from "./store";

describe("URL state", () => {
  it("round-trips the map", () => {
    const s = parseHash("#/map?lang=fr&place=saint-avold");
    expect(s).toMatchObject({ view: "map", lang: "fr", place: "saint-avold" });
    expect(parseHash(toHash(s))).toEqual(s);
    // links from the time of the colour modes still open the Settlements map
    expect(toHash(parseHash("#/map?color=holder&lang=fr&c=a,b"))).toBe("#/map?lang=fr");
  });
  it("round-trips the other views", () => {
    for (const hash of ["#/territories?lang=de&h=feudal&lvl=0", "#/holders?lang=en&entity=x",
      "#/map?lang=ja&layer=abbeys", "#/table?lang=fr&d=provostship-nancy&t=fief&q=chasteau"]) {
      expect(toHash(parseHash(hash))).toBe(hash);
    }
  });
  it("opens the former Church & resources tab in Settlements", () => {
    expect(toHash(parseHash("#/church?lang=en&layer=chaumes"))).toBe("#/map?lang=en&layer=chaumes");
    expect(toHash(parseHash("#/church?lang=en"))).toBe("#/map?lang=en&layer=abbeys");
    // a layer belongs to Settlements: other views don't carry it in their link
    expect(toHash({ ...parseHash("#/map?lang=en&layer=towns"), view: "table" })).toBe("#/table?lang=en");
  });
  it("falls back to defaults", () => {
    const s = parseHash("#/nowhere?color=rainbow&lang=xx&lvl=9&layer=x");
    expect(s.view).toBe("map");
    expect(s.level).toBeUndefined();
    expect(s.layer).toBeUndefined();
  });
  it("has no year", () => {
    expect(toHash(parseHash(""))).not.toContain("year");
  });
});
