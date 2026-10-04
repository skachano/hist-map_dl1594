// Screenshot at a given centre and zoom: node scripts/zoom.mjs <hash> <lon> <lat> <zoom> <out.png>
import { chromium } from "playwright";
const [hash, lon, lat, zoom, out] = process.argv.slice(2);
const browser = await chromium.launch({ args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
await page.goto(`${process.env.APP_URL ?? "http://localhost:5174"}/${hash}`);
await page.waitForSelector("#map canvas", { state: "attached" });
await page.waitForFunction(() => window.__map?.loaded());
await page.evaluate(([x, y, z]) => window.__map.jumpTo({ center: [x, y], zoom: z }), [Number(lon), Number(lat), Number(zoom)]);
await page.waitForTimeout(3000);
await page.screenshot({ path: out });
await browser.close();
