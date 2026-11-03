// Records replays of the real UI at 1920x1080. Usage: node capture.js <outdir> <name> <url> [<name> <url> ...]
const { chromium } = require(process.env.PW || "playwright-core");
const fs = require("fs");
const path = require("path");
(async () => {
  const [out, ...pairs] = process.argv.slice(2);
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
  for (let i = 0; i < pairs.length; i += 2) {
    const [name, url] = [pairs[i], pairs[i + 1]];
    const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1,
      recordVideo: { dir: out, size: { width: 1920, height: 1080 } } });
    const page = await ctx.newPage();
    const t0 = Date.now();
    await page.goto(url);
    await page.getByText("Conversation over.").first().waitFor({ timeout: 120000 });
    const tEnd = (Date.now() - t0) / 1000;
    await page.waitForTimeout(3000);
    await page.screenshot({ path: path.join(out, name + "-end.png") });
    const v = page.video();
    await ctx.close();
    fs.renameSync(await v.path(), path.join(out, name + ".webm"));
    console.log(name, "conversation over at", tEnd.toFixed(1), "s");
  }
  await browser.close();
})();
