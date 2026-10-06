import { describe, expect, it } from "vitest";
import { labelPoint } from "./labelPoint";

describe("label point", () => {
  it("sits in the middle of a square", () => {
    const [x, y] = labelPoint({ type: "Polygon", coordinates: [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]] })!;
    expect(Math.abs(x - 1)).toBeLessThan(0.1);
    expect(Math.abs(y - 1)).toBeLessThan(0.1);
  });
  it("stays inside a concave shape and picks the largest part", () => {
    // an L: its bounding-box centre (1.5, 1.5) is outside it
    const L = [[[0, 0], [3, 0], [3, 1], [1, 1], [1, 3], [0, 3], [0, 0]]];
    const tiny = [[[10, 10], [10.1, 10], [10.1, 10.1], [10, 10.1], [10, 10]]];
    const [x, y] = labelPoint({ type: "MultiPolygon", coordinates: [tiny, L] })!;
    expect(x < 1 || y < 1).toBe(true);
    expect(x).toBeLessThan(3);
  });
});
