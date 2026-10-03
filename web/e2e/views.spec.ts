import { expect, type Page, test } from "@playwright/test";
import { open } from "./helpers";

type M = { getZoom(): number; getCenter(): { lng: number; lat: number }; isMoving(): boolean };
const mapState = (page: Page) => page.evaluate(() => {
  const m = (window as unknown as { __map: M }).__map;
  return { zoom: m.getZoom(), moving: m.isMoving(), ...m.getCenter() };
});

test("territories: the two hierarchies and their levels", async ({ page }) => {
  const errors = await open(page, "#/territories?lang=en");
  const side = page.locator("#side");
  const pressed = (name: string) => expect(side.getByRole("button", { name, exact: true })).toHaveAttribute("aria-pressed", "true");
  await pressed("Administrative divisions");
  await pressed("Bailliages");
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toBeVisible();
  await expect(side.getByRole("button", { name: "Provostship of Nancy" })).toHaveCount(0);
  await expect(page.locator(".terr-label").filter({ hasText: "Bailiwick of Nancy" })).toHaveCount(1);

  await side.getByRole("button", { name: "Prévôtés, offices" }).click();
  await expect(page).toHaveURL(/lvl=2/);
  await expect(side.getByRole("button", { name: "Provostship of Nancy" })).toBeVisible();
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toHaveCount(0);
  await side.getByRole("button", { name: "All levels" }).click();
  await expect(page).toHaveURL(/lvl=0/);
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toBeVisible();
  await expect(side.getByRole("button", { name: "Provostship of Nancy" })).toBeVisible();

  // feudal realms: counties and lordships, not the duke's divisions
  await side.getByRole("button", { name: "Feudal realms" }).click();
  await expect(page).toHaveURL(/h=feudal/);
  await expect(side.getByRole("button", { name: "County of Vaudémont" })).toBeVisible();
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("territories: a member link walks down a level, a chain link back up", async ({ page }) => {
  await open(page, "#/territories?lang=en&place=bailiwick-nancy&lvl=1");
  const side = page.locator("#side");
  const panel = page.locator("#panel");
  await expect(panel.locator("h2")).toHaveText("Bailiwick of Nancy");
  await panel.locator(".members").getByRole("button", { name: "Provostship of Nancy" }).click();
  await expect(page).toHaveURL(/place=provostship-nancy/);
  await expect(page).toHaveURL(/lvl=2/);
  await expect(side.getByRole("button", { name: "Prévôtés, offices" })).toHaveAttribute("aria-pressed", "true");
  // the provostship's places, in the book's order: Nancy is entry 1
  await expect(panel.locator("ul.members.cols li").first()).toContainText("1 Nancy");
  await panel.locator(".crumbs").getByRole("button", { name: "Bailiwick of Nancy" }).click();
  await expect(page).toHaveURL(/lvl=1/);
  await expect(panel.locator("h2")).toHaveText("Bailiwick of Nancy");
});

test("a realm link opens the feudal realms, fitted to the realm", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en&place=vezelise");
  const panel = page.locator("#panel");
  await panel.locator(".crumbs").getByRole("button", { name: "County of Vaudémont" }).click();
  await expect(page).toHaveURL(/#\/territories\?.*place=county-vaudemont/);
  expect(page.url()).toContain("h=feudal");
  await expect(page.locator("#side").getByRole("button", { name: "Feudal realms" })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(async () => { const m = await mapState(page); return !m.moving && m.zoom > 8; }).toBe(true);
  const c = await mapState(page); // Vaudémont: about 48.4 N, 6.05 E
  expect(Math.abs(c.lng - 6.05)).toBeLessThan(0.5);
  expect(Math.abs(c.lat - 48.4)).toBeLessThan(0.4);
});

test("holders: pick a holder, see their realms and places", async ({ page }) => {
  await open(page, "#/holders?lang=en");
  const side = page.locator("#side");
  const menu = side.getByRole("combobox", { name: "Holder" });
  await expect(menu).toHaveValue("duchy-lorraine");
  await expect(side).toContainText("Realms held");
  await expect(side.getByRole("button", { name: "County of Vaudémont" })).toBeVisible();
  await expect(side.locator("h3").filter({ hasText: "ducal domain" })).toContainText(/\(\d{3}\)/);
  const other = await menu.locator("option").nth(1).getAttribute("value");
  await menu.selectOption(other!);
  await expect(page).toHaveURL(new RegExp(`entity=${other}`));
  await expect(side.getByRole("button", { name: "County of Vaudémont" })).toHaveCount(0);
});

test("table: filter by district, holder and words, export CSV, open a place", async ({ page }) => {
  await open(page, "#/table?lang=en");
  const rows = page.locator("table.matrix tbody tr");
  await expect(rows).toHaveCount(2485);
  const count = page.locator("#page .toolbar .muted");
  await expect(count).toHaveText("2485 entries");
  // a bailliage includes its prévôtés
  await page.getByRole("combobox", { name: "District" }).selectOption("bailiwick-nancy");
  await expect(page).toHaveURL(/d=bailiwick-nancy/);
  await expect.poll(() => rows.count()).toBeLessThan(2485);
  const inNancy = await rows.count();
  expect(inNancy).toBeGreaterThan(300);
  await expect(rows.first()).toContainText("Provostship of Nancy");
  await page.getByRole("combobox", { name: "Holders" }).selectOption("duchy-lorraine");
  await expect.poll(() => rows.count()).toBeLessThan(inNancy);
  await page.getByRole("searchbox", { name: "Words" }).fill("chasteau");
  await page.getByRole("searchbox", { name: "Words" }).press("Enter");
  await expect(page).toHaveURL(/q=chasteau/);
  for (const text of await rows.locator("td:nth-child(2)").allInnerTexts()) expect(text.toLowerCase()).toContain("chasteau");
  // scrolling the table keeps the toolbar in view and the column headers stuck to its top
  await page.getByRole("searchbox", { name: "Words" }).fill("");
  await page.getByRole("searchbox", { name: "Words" }).press("Enter");
  const toolbar = page.locator("#page .toolbar");
  const before = (await toolbar.boundingBox())!;
  await page.locator(".table-wrap").evaluate((el) => { el.scrollTop = 3000; });
  expect((await toolbar.boundingBox())!.y).toBe(before.y);
  const wrap = (await page.locator(".table-wrap").boundingBox())!;
  expect(Math.abs((await page.locator("table.matrix thead th").first().boundingBox())!.y - wrap.y)).toBeLessThan(3);

  const shown = await rows.count();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("denombrement-1594.csv");
  const stream = await file.createReadStream();
  const text = await new Promise<string>((resolve) => {
    let s = ""; stream.on("data", (c) => (s += c)); stream.on("end", () => resolve(s));
  });
  const lines = text.trim().split("\n");
  expect(lines[0]).toBe("No.,Entry,Place,District,Realm,Section or list,Holders,p.");
  expect(lines[1]).toMatch(/^1,"Nancy, palais/);
  expect(lines.length).toBeGreaterThanOrEqual(shown + 1); // a header, then a line or more per row

  await rows.first().getByRole("button", { name: "Nancy", exact: true }).click(); // a place opens on the map…
  await expect(page).toHaveURL(/#\/map\?.*place=nancy/);
  await expect(page.locator("#panel h2")).toHaveText("Nancy");
  await expect.poll(async () => (await mapState(page)).zoom).toBeGreaterThanOrEqual(11); // …zoomed in on it
  const c = await mapState(page);
  expect(Math.abs(c.lng - 6.1836)).toBeLessThan(0.02);
  expect(Math.abs(c.lat - 48.6928)).toBeLessThan(0.02);
});

test("church & resources: thematic lists on the map, chaumes listed", async ({ page }) => {
  const errors = await open(page, "#/church?lang=en");
  const side = page.locator("#side");
  await expect(side.getByRole("button", { name: "Abbeys" })).toHaveAttribute("aria-pressed", "true");
  await expect(side.locator("ul.entries li").first()).toContainText("2378");
  await side.getByRole("button", { name: "Towns" }).click();
  await expect(page).toHaveURL(/layer=towns/);
  await side.getByRole("button", { name: "Chaumes" }).click();
  await expect(side).toContainText("gîtes");
  await side.getByRole("button", { name: "Abbeys" }).click();
  await side.locator("ul.entries li button").first().click();
  await expect(page).toHaveURL(/#\/map\?.*place=/);
  await expect(page.locator("#panel h2")).toBeVisible();
  expect(errors).toEqual([]);
});

test("about page cites the book and the data sources in every language", async ({ page }) => {
  await open(page, "#/map?lang=en");
  await page.getByRole("button", { name: "About & sources" }).click();
  const about = page.locator("article.about");
  await expect(about).toContainText("H. L. et A. de B.");
  await expect(about).toContainText("GeoNames");
  await expect(about).toContainText("OpenStreetMap");
  for (const [lang, title] of [["Français", "À propos et sources"], ["Deutsch", "Über & Quellen"], ["日本語", "解説と出典"]]) {
    await page.getByRole("button", { name: lang }).click();
    await expect(about.locator("h2").first()).toHaveText(title);
  }
});
