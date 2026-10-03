import { describe, expect, it } from "vitest";
import type { Dataset, Place } from "../data/types";
import { chains, isShared, mainHolding, placeStyles, ressortOf } from "./places";
import { TENURE_COLOURS } from "./colors";

const P = (p: Partial<Place> & { id: string }): Place => ({ kind: "territory", type: "village", name: { fr: p.id }, ...p });
const places = new Map<string, Place>([
  ["duchy-lorraine", P({ id: "duchy-lorraine", type: "duchy", h: "admin" })],
  ["bailiwick-nancy", P({ id: "bailiwick-nancy", type: "bailiwick", h: "admin", parents: [{ id: "duchy-lorraine", rel: "admin" }] })],
  ["provostship-nancy", P({ id: "provostship-nancy", type: "provostship", h: "admin",
    parents: [{ id: "bailiwick-nancy", rel: "admin" }] })],
  ["provostship-rosieres", P({ id: "provostship-rosieres", type: "provostship", h: "admin",
    parents: [{ id: "bailiwick-nancy", rel: "admin" }] })],
  ["lordship-pierrefort", P({ id: "lordship-pierrefort", type: "lordship", h: "feudal",
    parents: [{ id: "provostship-nancy", rel: "ressort" }] })],
  ["temporality-abbey-x", P({ id: "temporality-abbey-x", type: "temporality", h: "feudal" })],
  ["pierrefort", P({ id: "pierrefort", kind: "settlement", lat: 48.8, lon: 5.9,
    parents: [{ id: "provostship-nancy", rel: "admin" }, { id: "lordship-pierrefort", rel: "feudal" }],
    hold: [{ t: "fief", e: [104] }] })],
  ["einvaux", P({ id: "einvaux", kind: "settlement", lat: 48.5, lon: 6.4,
    parents: [{ id: "provostship-rosieres", rel: "admin", share: "part" }, { id: "provostship-nancy", rel: "admin" }],
    hold: [{ t: "clergy", e: [145] }, { t: "domain", h: "duchy-lorraine", share: "part", e: [200] }] })],
  ["guessling", P({ id: "guessling", kind: "settlement", lat: 49.0, lon: 6.7,
    parents: [{ id: "temporality-abbey-x", rel: "feudal" }], hold: [{ t: "clergy", h: "abbey-x", e: [2268] }] })],
]);
const data = { places, entities: new Map() } as unknown as Dataset;

describe("places", () => {
  it("follows each hierarchy up to (not including) the duchy", () => {
    expect(chains("pierrefort", "admin", places)).toEqual([["provostship-nancy", "bailiwick-nancy"]]);
    expect(chains("pierrefort", "feudal", places)).toEqual([["lordship-pierrefort"]]);
    expect(chains("einvaux", "admin", places)).toHaveLength(2);   // two prévôtés, "en partie"
    expect(ressortOf("lordship-pierrefort", places)).toBe("provostship-nancy");
  });
  it("puts domain before other tenures", () => {
    expect(mainHolding(places.get("einvaux")!)?.t).toBe("domain");
    expect(isShared(places.get("einvaux")!)).toBe(true);
    expect(isShared(places.get("pierrefort")!)).toBe(false);
  });
  it("colours places by their main tenure", () => {
    expect(placeStyles(data).get("pierrefort")?.fill).toBe(TENURE_COLOURS.fief);
    expect(placeStyles(data).get("einvaux")).toEqual({ fill: TENURE_COLOURS.domain, shared: true });
  });
});
