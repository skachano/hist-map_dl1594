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
