// capture-v3.mjs — 补 detail（学习工作台+四维依据）与 wbr blocks，合并进 live-layout.json
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const CHROME = 'C:/Users/HECHUAN/AppData/Local/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-win64/chrome-headless-shell.exe';
const BASE = 'http://127.0.0.1:5174';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../public/textures/live');
const LAYOUT = path.resolve(HERE, '../src/aifl/live-layout.json');

const browser = await puppeteer.launch({
  executablePath: CHROME,
  args: ['--no-sandbox', '--force-device-scale-factor=2', '--font-render-hinting=none'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
const settle = async (ms = 1000) => {
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, ms));
};
const box = (el) =>
  el.evaluate((e) => {
    const r = e.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
  });

const layout = JSON.parse(fs.readFileSync(LAYOUT, 'utf-8'));

// ---- detail：先切到编程空间（有独立证据），再截工作台 ----
await page.goto(BASE + '/app?view=learning', { waitUntil: 'networkidle0', timeout: 60000 });
await settle();
const opened = await page.evaluate(() => {
  const row = [...document.querySelectorAll('.learning-recent-row')]
    .find((e) => /Python/.test(e.textContent || ''));
  if (row) { row.click(); return true; }
  return false;
});
console.log('opened python space via recent-row:', opened);
await settle(1600);
let evRows = await page.$$('.evidence-four > article');
if (!evRows.length) {
  // 兜底：current 卡的继续学习按钮
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('.learning-current-card button')]
      .find((e) => /继续学习/.test(e.textContent || ''));
    if (b) b.click();
  });
  await settle(1600);
  evRows = await page.$$('.evidence-four > article');
}
console.log('evidence rows found:', evRows.length);
await page.screenshot({ path: `${OUT}/detail-full.png`, fullPage: true });
layout.detail = { pageH: await page.evaluate(() => document.documentElement.scrollHeight), rows: [] };
for (const r of evRows) layout.detail.rows.push(await box(r));
console.log('detail rows:', layout.detail.rows.length, 'pageH', layout.detail.pageH);

// ---- wbr：示例页讲义正文块 ----
await page.goto(BASE + '/examples', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1200);
await page.screenshot({ path: `${OUT}/wbr-full.png`, fullPage: true });
layout.wbr.pageH = await page.evaluate(() => document.documentElement.scrollHeight);
const sel = '.entry-tab-body header h2, .entry-tab-body header span, .entry-question-strip, ' +
  '.entry-tab-body > p, .entry-example-equations > div > p, .entry-price-bars, .entry-takeaway, ' +
  '.entry-sample-question h3, .entry-sample-question > div > p, .entry-sample-question fieldset, ' +
  '.entry-example-actions';
const blocks = await page.$$(sel);
layout.wbr.blocks = [];
for (const b of blocks.slice(0, 20)) {
  const bb = await box(b);
  const tag = await b.evaluate((e) => e.tagName.toLowerCase());
  layout.wbr.blocks.push({ ...bb, tag: tag === 'h2' ? 'h2' : 'p' });
}
console.log('wbr blocks:', layout.wbr.blocks.length);
layout.wbr.leftRail = await box(await page.$('.entry-example-selector'));
layout.wbr.rightRail = await box(await page.$('.entry-sample-question'));

fs.writeFileSync(LAYOUT, JSON.stringify(layout, null, 1));
console.log('wrote', LAYOUT);
await browser.close();
console.log('CAPTURE V3 DONE');
