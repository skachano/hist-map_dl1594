import { describe, expect, it } from "vitest";
import type { Dataset } from "../data/types";
import { chaumeTotals } from "./sideViews";

const chaume = (provostship: string, gistes?: number) =>
  ({ id: `c-${Math.random()}`, theme: "chaume", name: "x", attrs: { provostship, ...(gistes ? { gistes } : {}) } });

describe("chaumes", () => {
  it("adds up each provostship's gîtes and shades the largest darkest", () => {
    const data = { features: [chaume("provostship-arches", 4), chaume("provostship-arches", 28),
      chaume("provostship-arches"), chaume("provostship-saint-die", 1)] } as unknown as Dataset;   // the plain has no count
    const totals = chaumeTotals(data);
    expect(totals.get("provostship-arches")?.gistes).toBe(32);
    expect(totals.get("provostship-saint-die")?.gistes).toBe(1);
    const lightness = (hex: string) => parseInt(hex.slice(1, 3), 16) + parseInt(hex.slice(3, 5), 16);
    expect(lightness(totals.get("provostship-arches")!.colour))
      .toBeLessThan(lightness(totals.get("provostship-saint-die")!.colour));
  });
});
