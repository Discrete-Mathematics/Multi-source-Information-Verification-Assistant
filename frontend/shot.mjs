import { chromium } from "playwright";

const URL = process.env.APP_URL || "http://127.0.0.1:8000/";
const OUT = process.env.OUT || "/tmp/factcheck-shot.png";

const launchOpts = { args: ["--no-sandbox"] };
if (process.env.CHROME_PATH) launchOpts.executablePath = process.env.CHROME_PATH;

const browser = await chromium.launch(launchOpts);
const page = await browser.newPage({ viewport: { width: 1380, height: 1100 } });
await page.goto(URL, { waitUntil: "networkidle" });

// Fill the example and run a verification.
await page.click("text=示例 2"); // Einstein Nobel example (has a refuted sub-claim)
await page.click("text=开始核验");

// Wait until at least one verdict badge appears, then a bit more for all claims.
await page.waitForSelector(".verdict-badge", { timeout: 180000 });
await page.waitForTimeout(4000);
// Wait for overall gauge (report done) if it shows up.
await page.waitForSelector(".gauge", { timeout: 60000 }).catch(() => {});
await page.waitForTimeout(1500);

await page.screenshot({ path: OUT, fullPage: true });
console.log("saved", OUT);
await browser.close();
