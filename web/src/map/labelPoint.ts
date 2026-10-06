// Where to put an area's label: the point inside its largest part that lies farthest from the
// edges (a grid search for the "pole of inaccessibility"), so a label sits in the middle of the
// shape even when the shape is concave or the seat lies near a border.

type Ring = number[][];
type Polygon = Ring[];

function area(ring: Ring): number {
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  return Math.abs(a / 2);
}

function inside(x: number, y: number, polygon: Polygon): boolean {
  let hit = false;
  for (const ring of polygon) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i], [xj, yj] = ring[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
    }
  }
  return hit;
}

function edgeDistance(x: number, y: number, polygon: Polygon): number {
  let best = Infinity;
  for (const ring of polygon) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [ax, ay] = ring[j], [bx, by] = ring[i];
      const dx = bx - ax, dy = by - ay;
      const t = dx || dy ? Math.max(0, Math.min(1, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))) : 0;
      best = Math.min(best, Math.hypot(x - (ax + t * dx), y - (ay + t * dy)));
    }
  }
  return best;
}

/** The label point of a Polygon or MultiPolygon, as [lon, lat]; undefined for other geometries. */
export function labelPoint(geometry: GeoJSON.Geometry, steps = 40): [number, number] | undefined {
  const polygons: Polygon[] = geometry.type === "Polygon" ? [geometry.coordinates]
    : geometry.type === "MultiPolygon" ? geometry.coordinates : [];
  if (!polygons.length) return undefined;
  const polygon = polygons.reduce((a, b) => (area(b[0]) > area(a[0]) ? b : a));
  const xs = polygon[0].map((p) => p[0]), ys = polygon[0].map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  // longitude degrees are shorter than latitude ones: measure in a locally equal-area frame
  const k = Math.cos(((y0 + y1) / 2) * (Math.PI / 180));
  const scaled = polygon.map((ring) => ring.map(([x, y]) => [x * k, y]));
  let best: [number, number] | undefined, bestD = -1;
  for (let i = 0; i <= steps; i++) {
    for (let j = 0; j <= steps; j++) {
      const x = x0 + ((x1 - x0) * i) / steps, y = y0 + ((y1 - y0) * j) / steps;
      if (!inside(x * k, y, scaled)) continue;
      const d = edgeDistance(x * k, y, scaled);
      if (d > bestD) [best, bestD] = [[x, y], d];
    }
  }
  return best;
}
