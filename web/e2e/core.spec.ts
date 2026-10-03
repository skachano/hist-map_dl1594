import { expect, test } from "@playwright/test";
import { legendTitle, mapSettled, open } from "./helpers";

test("colour modes change what the map shows and the URL", async ({ page }) => {
  const errors = await open(page, "#/map?color=tenure&lang=en");
  const tabs = page.getByRole("navigation", { name: "Colour by" });
  await expect(tabs.getByRole("button", { name: "Tenure" })).toHaveAttribute("aria-pressed", "true");
  await expect(tabs.getByRole("button")).toHaveCount(2);   // districts and realms are the Territories view's
  const before = await legendTitle(page).innerText();
  await tabs.getByRole("button", { name: "Holder", exact: true }).click();
  await expect(page).toHaveURL(/color=holder/);
  await expect(legendTitle(page)).not.toHaveText(before);
  expect(errors).toEqual([]);
});

test("language switch translates the interface and the names", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en&place=saint-avold");
  await expect(page.locator("#panel h2")).toHaveText("Saint-Avold");
  await page.getByRole("button", { name: "Deutsch" }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "de");
  await expect(page.locator("#header h1")).toHaveText("Das Herzogtum Lothringen 1594");
  await expect(page.getByRole("button", { name: "Besitzart" })).toBeVisible();
  await expect(page.locator("#panel h2")).toHaveText("Sankt Avold");
  await page.getByRole("button", { name: "Français" }).click();
  await expect(page.locator("#header h1")).toHaveText("Le duché de Lorraine en 1594");
  await page.getByRole("button", { name: "日本語" }).click();
  await expect(page).toHaveURL(/lang=ja/);
  await expect(page.locator("#header h1")).toHaveText("1594年のロレーヌ公国");
});

test("place panel lists every entry naming the place, with numbers, sections and pages", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en&place=saint-avold");
  const panel = page.locator("#panel");
  await expect(panel).toContainText("FR Saint-Avold · DE Sankt Avold · EN Saint-Avold");
  const entries = panel.locator("ul.entries > li");
  await expect(entries).toHaveCount(4);
  await expect(entries.nth(0)).toContainText("No. 2240");
  await expect(entries.nth(0)).toContainText("La ville de Sainct-Avol ou Sataet-Nabor");
  await expect(entries.nth(0)).toContainText("p. 114");
  await expect(entries.nth(1)).toContainText("No. 2267");
  await expect(entries.nth(1)).toContainText("p. 115");
  // held twice: the duke's domain (the town) and church lands (the abbey)
  const holdings = panel.locator("ul.holdings > li");
  await expect(holdings).toHaveCount(2);
  await expect(holdings.nth(0)).toContainText("Duke of Lorraine");
  await expect(holdings.nth(1)).toContainText("Holder not named");
  await panel.getByRole("button", { name: "Close" }).click();
  await expect(panel).toBeHidden();
  await expect(page).not.toHaveURL(/place=/);
});

test("a place split between two prévôtés shows both district chains", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en&place=athienville");
  const crumbs = page.locator("#panel .crumbs");
  await expect(crumbs).toHaveCount(2);
  await expect(crumbs.nth(0)).toContainText("Bailiwick of Nancy");
  await expect(crumbs.getByRole("button", { name: "Provostship of Einville" })).toBeVisible();
  await expect(crumbs.getByRole("button", { name: "Provostship of Lunéville" })).toBeVisible();
  await expect(page.locator("#panel ul.entries > li")).toHaveCount(2); // entries 234 and 267
});

test("keyboard: panel takes focus, Escape closes it and returns focus; skip link", async ({ page }) => {
  await open(page, "#/territories?lang=en");
  const link = page.locator("#side").getByRole("button", { name: "Bailiwick of Nancy" });
  await link.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#panel h2")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.locator("#panel")).toBeHidden();
  await expect(link).toBeFocused();
  await open(page, "#/map?color=tenure&lang=en");
  await page.reload(); // a hash change keeps focus where it was; the skip link is for a fresh page
  await expect(page.locator("#header h1")).toBeVisible();
  await page.keyboard.press("Tab");
  const skip = page.getByRole("button", { name: /Skip the map/ });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#\/table/);
});

test("the hover tooltip stays inside the map near the edges (no scrollbar)", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en");
  await mapSettled(page); // a drag during the opening fit is lost
  const box = (await page.locator("#map").boundingBox())!;
  // drag the duchy into the bottom-right corner, so villages sit at the map's edges
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.97, box.y + box.height * 0.95, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(500);
  const tooltip = page.locator("#tooltip");
  let found = false;
  for (let y = box.y + box.height - 8; y > box.y + box.height - 200 && !found; y -= 6) {
    for (let x = box.x + box.width - 8; x > box.x + box.width - 240 && !found; x -= 6) {
      await page.mouse.move(x, y);
      found = await tooltip.isVisible();
    }
  }
  expect(found).toBe(true);
  const tip = (await tooltip.boundingBox())!;
  expect(tip.x + tip.width).toBeLessThanOrEqual(box.x + box.width);
  expect(tip.y + tip.height).toBeLessThanOrEqual(box.y + box.height);
  const scroll = await page.evaluate(() => ({
    x: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    y: document.documentElement.scrollHeight - document.documentElement.clientHeight,
  }));
  expect(scroll).toEqual({ x: 0, y: 0 });
});

test("settlements are drawn with one shape per kind of place, keyed in the legend", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en");
  const key = page.locator("#legend ul.shapes");
  await expect(key.locator("li").first()).toBeVisible();
  await expect(key.locator("svg")).toHaveCount(await key.locator("li").count());
  await page.waitForFunction(() => (window as unknown as { __map?: { loaded(): boolean } }).__map?.loaded());
  const images = await page.evaluate(() => {
    const map = (window as unknown as { __map: { hasImage(id: string): boolean } }).__map;
    return ["place-village", "place-town", "place-abbey"].map((id) => map.hasImage(id));
  });
  expect(images).toEqual([true, true, true]);
});

test("spellings by source: the lists, the editor's index and the table of old forms", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en&place=croismare");
  const spell = page.locator("#panel dd.spell");
  await expect(spell.filter({ hasText: "In the lists" })).toContainText("(255)");
  await expect(spell.filter({ hasText: "In the editor's index (1870)" })).toContainText("Croismare (255)");
  await expect(spell.filter({ hasText: "Table of old forms" })).toContainText("Hadonviller");
});

test("an entry naming two places is listed under both, each linking the other", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en&place=woelfling");
  const entry = page.locator("#panel ul.entries > li").filter({ hasText: "No. 2230" });
  await expect(entry).toBeVisible();
  await entry.getByRole("button", { name: "Wiesviller" }).click();
  await expect(page.locator("#panel h2")).toHaveText("Wiesviller");
  await expect(page.locator("#panel ul.entries > li").filter({ hasText: "No. 2230" })
    .getByRole("button", { name: /^W(oe|œ)lfling/ })).toBeVisible();
  await open(page, "#/table?lang=en&q=Volfflingcn");
  const row = page.locator("table.matrix tbody tr").first();
  await expect(row.getByRole("button", { name: /^W(oe|œ)lfling/ })).toBeVisible();
  await expect(row.getByRole("button", { name: "Wiesviller" })).toBeVisible();
});
