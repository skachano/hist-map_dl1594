import { describe, expect, it } from "vitest";
import { MAP_CENTER, YEAR } from "./config";

describe("config", () => {
  it("describes 1594", () => expect(YEAR).toBe(1594));
  it("centres the map in Lorraine", () => {
    const [lon, lat] = MAP_CENTER;
    expect(lon).toBeGreaterThan(5.3);
    expect(lon).toBeLessThan(7.7);
    expect(lat).toBeGreaterThan(47.8);
    expect(lat).toBeLessThan(49.9);
  });
});
