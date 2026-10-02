import { describe, expect, it } from "vitest";
import type { Dataset, Entry, Place } from "../data/types";
import { entryHolders, filterEntries } from "./pages";

const place = (id: string, kind: Place["kind"], parent?: string) =>
  [id, { id, kind, type: kind === "settlement" ? "village" : "provostship", name: { fr: id },
    parents: parent ? [{ id: parent, rel: "admin" }] : [] }] as const;
const entries: Entry[] = [
  { no: 1, text: "Nancy, ville capitale.", name: "Nancy", district: "provostship-nancy", section: "domain" },
  { no: 2, text: "Laxou.", name: "Laxou", district: "provostship-nancy", section: "fief", holders: ["count-salm"] },
  { no: 3, text: "Mirecourt.", name: "Mirecourt", district: "bailiwick-vosges", section: "domain" },
  { no: 2378, text: "Sainct-Martin, de Nancy.", name: "Sainct-Martin", series: "abbeys_m" },
];
const data = {
  entries,
  places: new Map<string, Place>([
    place("bailiwick-nancy", "territory"), place("provostship-nancy", "territory", "bailiwick-nancy"),
    place("bailiwick-vosges", "territory"),
  ] as unknown as [string, Place][]),
} as unknown as Dataset;

describe("table", () => {
  it("gives domain to the duke unless the book names a holder", () => {
    expect(entryHolders(entries[0])).toEqual(["duchy-lorraine"]);
    expect(entryHolders(entries[1])).toEqual(["count-salm"]);
    expect(entryHolders(entries[3])).toEqual([]);
  });
  it("filters by a district and the divisions below it", () => {
    expect(filterEntries(data, { district: "bailiwick-nancy" }).map((e) => e.no)).toEqual([1, 2]);
  });
  it("filters by holder, list and words", () => {
    expect(filterEntries(data, { holder: "duchy-lorraine" }).map((e) => e.no)).toEqual([1, 3]);
    expect(filterEntries(data, { series: "abbeys_m" }).map((e) => e.no)).toEqual([2378]);
    expect(filterEntries(data, { series: "main" }).map((e) => e.no)).toEqual([1, 2, 3]);
    expect(filterEntries(data, { q: "nancy VILLE" }).map((e) => e.no)).toEqual([1]);
  });
});
