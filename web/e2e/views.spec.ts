import { expect, type Page, test } from "@playwright/test";
import { open } from "./helpers";

type M = { getZoom(): number; getCenter(): { lng: number; lat: number }; isMoving(): boolean };
const mapState = (page: Page) => page.evaluate(() => {
  const m = (window as unknown as { __map: M }).__map;
  return { zoom: m.getZoom(), moving: m.isMoving(), ...m.getCenter() };
});

test("territories: the two hierarchies and their levels", async ({ page }) => {
  // levels by kind: the district of Bitche, under the duchy, is an office; its mairies are mairies
  const errors = await open(page, "#/territories?lang=en");
  const side = page.locator("#side");
  const pressed = (name: string) => expect(side.getByRole("button", { name, exact: true })).toHaveAttribute("aria-pressed", "true");
  await pressed("Administrative divisions");
  await pressed("Bailiwicks");
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toBeVisible();
  await expect(side.getByRole("button", { name: "Provostship of Nancy" })).toHaveCount(0);
  await expect(page.locator(".terr-label").filter({ hasText: "Bailiwick of Nancy" })).toHaveCount(1);

  await side.getByRole("button", { name: "Provostships, offices" }).click();
  await expect(page).toHaveURL(/lvl=2/);
  await expect(side.getByRole("button", { name: "Provostship of Nancy" })).toBeVisible();
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toHaveCount(0);
  await expect(side.getByRole("button", { name: "District of Bitche" })).toBeVisible();
  await side.getByRole("button", { name: "Bans, mayoralties" }).click();
  await expect(side.getByRole("button", { name: "Mayoralty of Schorbach" })).toBeVisible();
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
  await expect(side.getByRole("button", { name: "Provostships, offices" })).toHaveAttribute("aria-pressed", "true");
  // the provostship's places, in the book's order: Nancy is entry 1
  await expect(panel.locator("ul.members.cols li").first()).toContainText("1 Nancy");
  await panel.locator(".crumbs").getByRole("button", { name: "Bailiwick of Nancy" }).click();
  await expect(page).toHaveURL(/lvl=1/);
  await expect(panel.locator("h2")).toHaveText("Bailiwick of Nancy");
});

test("a realm link opens the feudal realms, fitted to the realm", async ({ page }) => {
  await open(page, "#/map?lang=en&place=vezelise");
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
  await expect(rows).toHaveCount(2486);
  const count = page.locator("#page .toolbar .muted");
  await expect(count).toHaveText("2486 entries");
  // a bailliage includes its prévôtés
  await page.getByRole("combobox", { name: "District" }).selectOption("bailiwick-nancy");
  await expect(page).toHaveURL(/d=bailiwick-nancy/);
  await expect.poll(() => rows.count()).toBeLessThan(2486);
  const inNancy = await rows.count();
  expect(inNancy).toBeGreaterThan(300);
  await expect(rows.first()).toContainText("Provostship of Nancy");
  await page.getByRole("combobox", { name: "Holders" }).selectOption("duchy-lorraine");
  await expect.poll(() => rows.count()).toBeLessThan(inNancy);
  await page.getByRole("searchbox", { name: "Words" }).fill("chasteau");
  await page.getByRole("searchbox", { name: "Words" }).press("Enter");
  await expect(page).toHaveURL(/q=chasteau/);
  for (const text of await rows.locator("td:nth-child(6)").allInnerTexts()) expect(text.toLowerCase()).toContain("chasteau");
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
  expect(lines[0]).toBe("Type,No.,Place,District,Tenure,Thierry Alix's entry,Editors' index");
  expect(lines[1]).toMatch(/^Town,1,Nancy,Provostship of Nancy,domain,"Nancy, palais .*\(p\. 35\)","Nancy, canton of Nancy \(p\. 233\)"$/);
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

test("territories: one kind of realm at every level, and the colour key of the kinds shown", async ({ page }) => {
  await open(page, "#/territories?lang=en");
  const side = page.locator("#side");
  const groups = side.locator("ul.groups li");
  await expect(groups.filter({ hasText: "Bailiwicks" })).toContainText("8");
  await expect(groups.filter({ hasText: "Offices, castellanies, provostships" })).toContainText("0");   // level 1: bailliages only
  const menu = side.getByRole("combobox", { name: "Kind of realm" });
  await menu.selectOption("provostship");
  await expect(page).toHaveURL(/kind=provostship/);
  await expect(side.getByRole("button", { name: "Bailiwicks" })).toHaveAttribute("aria-pressed", "false");
  for (const text of await side.locator("ul.realms li").allInnerTexts()) expect(text).toMatch(/^Provostship of /);
  await menu.selectOption("county");
  await expect(groups.filter({ hasText: "Counties" })).toContainText("3");
  await expect(side.getByRole("button", { name: "County of Vaudémont" })).toBeVisible();
  await side.getByRole("button", { name: "Administrative divisions" }).click();   // back to levels
  await expect(page).not.toHaveURL(/kind=/);
  await expect(side.getByRole("button", { name: "Bailiwick of Nancy" })).toBeVisible();
});

test("table: each row starts with its place's icon, and gives the pages of the entry and of the index", async ({ page }) => {
  await open(page, "#/table?lang=en&q=Frouart");
  const row = page.locator("table.matrix tbody tr").first();
  await expect(row.locator("td.type-cell svg.shape")).toHaveCount(1);
  await expect(row.locator("td.type-cell .type-icon")).toHaveAttribute("title", "Small town");
  await expect(row.locator("td").nth(4)).toHaveText("Frouart, bourg et chasteau. (p. 36)");
  await expect(row.locator("td").nth(5)).toHaveText(/^Frouard, canton of Nancy-Nord \(p\. 210\)$/);
  // the index's headings and cantons as printed, not as the scan misread them
  await open(page, "#/table?lang=en&q=Houdelmont");
  await expect(page.locator("table.matrix tbody tr").first().locator("td").nth(5))
    .toHaveText("Houdelmont, canton of Vézelise (p. 219)");
  await open(page, "#/table?lang=en&q=Arth-sur-Meurthe");
  await expect(page.locator("table.matrix tbody tr").first().locator("td").nth(5))
    .toHaveText("Art-sur-Meurthe, canton of Saint-Nicolas (p. 185)");
  // an entry whose number the index doesn't print shows its place's line, marked
  await open(page, "#/table?lang=en&q=Gerbéviller, chasteau, ville et prieuré");
  await expect(page.locator("table.matrix tbody tr").first().locator("td").nth(5))
    .toHaveText("Gerbéviller, canton of Gerbéviller (p. 211) [number not printed]");
  await expect(page.locator("table.matrix thead th")).toHaveText(
    ["Type", "No.", "Place", "District", "Tenure", "Thierry Alix's entry", "Editors' index"]);
});
