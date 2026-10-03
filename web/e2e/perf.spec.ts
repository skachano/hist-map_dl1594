// Performance budgets, measured with performance.measure() marks in src/main.ts.
import { expect, test } from "@playwright/test";
import { open } from "./helpers";

const measures = (page: import("@playwright/test").Page, prefix: string) =>
  page.evaluate((p) => performance.getEntriesByType("measure").filter((m) => m.name.startsWith(p)).map((m) => m.duration), prefix);

test("load, mode changes and the table stay within budget", async ({ page }) => {
  await open(page, "#/map?color=tenure&lang=en");
  const [load] = await measures(page, "load-data");
  const [firstRender] = await measures(page, "render:map");

  const tabs = page.getByRole("navigation", { name: "Colour by" });
  for (const name of ["Holder", "Tenure", "Holder", "Tenure", "Holder", "Tenure", "Holder", "Tenure"]) {
    await tabs.getByRole("button", { name, exact: true }).click();
  }
  await expect(tabs.getByRole("button", { name: "Tenure" })).toHaveAttribute("aria-pressed", "true");
  const steps = (await measures(page, "render:map")).slice(1);
  const slowestStep = Math.max(...steps);

  await page.getByRole("button", { name: "Table", exact: true }).click();
  await expect(page.locator("table.matrix tbody tr").first()).toBeVisible();
  const [table] = await measures(page, "render:table");

  console.log(JSON.stringify({ loadDataMs: Math.round(load), firstRenderMs: Math.round(firstRender),
    modeChangeMsMax: Math.round(slowestStep), tableMs: Math.round(table) }));
  expect(load + firstRender).toBeLessThan(3000);
  expect(slowestStep).toBeLessThan(200);
  expect(table).toBeLessThan(1500);
});
