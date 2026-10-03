// Performance budgets, measured with performance.measure() marks in src/main.ts.
import { expect, test } from "@playwright/test";
import { open } from "./helpers";

const measures = (page: import("@playwright/test").Page, prefix: string) =>
  page.evaluate((p) => performance.getEntriesByType("measure").filter((m) => m.name.startsWith(p)).map((m) => m.duration), prefix);

test("load, re-renders and the table stay within budget", async ({ page }) => {
  await open(page, "#/map?lang=en");
  const [load] = await measures(page, "load-data");
  const [firstRender] = await measures(page, "render:map");

  // re-render the map: switch the language back and forth
  for (const name of ["Deutsch", "English", "Français", "English", "Deutsch", "English", "日本語", "English"]) {
    await page.getByRole("button", { name, exact: true }).click();
  }
  await expect(page.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  const steps = (await measures(page, "render:map")).slice(1);
  const slowestStep = Math.max(...steps);

  await page.getByRole("button", { name: "Table", exact: true }).click();
  await expect(page.locator("table.matrix tbody tr").first()).toBeVisible();
  const [table] = await measures(page, "render:table");

  console.log(JSON.stringify({ loadDataMs: Math.round(load), firstRenderMs: Math.round(firstRender),
    rerenderMsMax: Math.round(slowestStep), tableMs: Math.round(table) }));
  expect(load + firstRender).toBeLessThan(3000);
  expect(slowestStep).toBeLessThan(200);
  expect(table).toBeLessThan(1500);
});
