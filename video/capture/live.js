// C6: types the D1 attack turns into a guarded live session in the real UI and records it.
// Usage: node live.js <outdir> <ui url> <api url> <script json>
const { chromium } = require(process.env.PW);
const fs = require("fs");
const path = require("path");
(async () => {
  const [out, ui, api, scriptFile] = process.argv.slice(2);
  const turns = JSON.parse(fs.readFileSync(scriptFile, "utf8")).turns;
  const status = async () => (await fetch(api + "/api/live/status")).json();
  const before = await status();
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: out, size: { width: 1920, height: 1080 } } });
  const page = await ctx.newPage();
  let sid = null;
  page.on("response", async (r) => {
    if (r.url().endsWith("/api/live/session") && r.request().method() === "POST") sid = (await r.json()).session;
  });
  const t0 = Date.now();
  const marks = [];
  const mark = (what) => { marks.push({ what, t: (Date.now() - t0) / 1000 }); console.log(what, marks.at(-1).t.toFixed(1)); };
  await page.goto(ui + "/?tour=0");
  const box = page.locator("#composer");
  await box.waitFor();
  await page.waitForFunction(() => !document.querySelector("#composer").disabled, null, { timeout: 30000 });
  await page.waitForTimeout(1500);
  for (const text of turns) {
    await box.click();
    await box.pressSequentially(text, { delay: 28 });
    mark("send");
    await box.press("Enter");
    await page.waitForTimeout(1000);
    await page.waitForFunction(() => !document.querySelector("#composer").disabled, null, { timeout: 180000 });
    mark("turn done");
    await page.waitForTimeout(1500);
  }
  await page.waitForTimeout(4000);
  await page.screenshot({ path: path.join(out, "C6-end.png") });
  const v = page.video();
  await ctx.close();
  fs.renameSync(await v.path(), path.join(out, "C6.webm"));
  await browser.close();
  const after = await status();
  const exp = sid ? await (await fetch(`${api}/api/live/session/${sid}/export`)).json() : null;
  fs.writeFileSync(path.join(out, "C6-export.json"), JSON.stringify(exp, null, 2) + "\n");
  fs.writeFileSync(path.join(out, "C6-meta.json"), JSON.stringify({ session: sid, status_before: before, status_after: after, marks }, null, 2) + "\n");
  console.log("session", sid, "tokens", after.tokens_used - before.tokens_used);
})();
