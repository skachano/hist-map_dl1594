// Runs in the desktop and phone projects: no view may be wider than the screen or log errors.
import { expect, test } from "@playwright/test";
import { open } from "./helpers";
import { VIEWS } from "./views";

for (const hash of VIEWS) {
  test(`layout ${hash}`, async ({ page }) => {
    const errors = await open(page, hash);
    await page.waitForTimeout(500);
    const width = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, screen: window.innerWidth }));
    expect(width.page).toBeLessThanOrEqual(width.screen);
    expect(errors).toEqual([]);
  });
}

test("the Settlements row stays scrolled where it was", async ({ page }) => {
  await open(page, "#/map?lang=en");
  const modes = page.locator("header .modes");
  const max = await modes.evaluate((el) => el.scrollWidth - el.clientWidth);
  test.skip(max <= 0, "the row fits the screen");
  await modes.evaluate((el) => { el.scrollLeft = el.scrollWidth; });
  const before = await modes.evaluate((el) => el.scrollLeft);
  await modes.locator("button").last().click();
  await expect(modes.locator("button").last()).toHaveAttribute("aria-pressed", "true");
  expect(await modes.evaluate((el) => el.scrollLeft)).toBe(before);
});
