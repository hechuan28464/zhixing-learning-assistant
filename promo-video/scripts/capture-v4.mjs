// capture-v4.mjs — 带登录态截真实导师对话页，重写 layout.wbr
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const CHROME = 'C:/Users/HECHUAN/AppData/Local/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-win64/chrome-headless-shell.exe';
const BASE = 'http://127.0.0.1:5174';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../public/textures/live');
const LAYOUT = path.resolve(HERE, '../src/aifl/live-layout.json');
const S_MATH = 'space_233c3ad66c0f41a2963cc2d876577d81';

const browser = await puppeteer.launch({
  executablePath: CHROME,
  args: ['--no-sandbox', '--force-device-scale-factor=2', '--font-render-hinting=none'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
const settle = async (ms = 1200) => {
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, ms));
};
const box = (el) =>
  el.evaluate((e) => {
    const r = e.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
  });

await page.goto(BASE + '/app', { waitUntil: 'networkidle0', timeout: 60000 });
const login = await page.evaluate(async () => {
  const r = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'demo', password: 'promo-demo-2026', remember: false }),
  });
  return r.status;
});
console.log('login status:', login);
await page.goto(BASE + '/app?view=buddy', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1500);
// 选中数学空间（真实对话所在）
const picked = await page.evaluate((sid) => {
  const sel = document.querySelector('.space-selector select');
  if (!sel) return false;
  sel.value = sid;
  sel.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}, S_MATH);
console.log('selected math space:', picked);
await settle(2000);
// 展开滚动容器与固定高度面板，让 fullPage 截到全部对话（composer 是 sticky，须一并解除）
await page.addStyleTag({ content:
  '.tutor-panel-live{height:auto!important;max-height:none!important;overflow:visible!important;position:static!important}' +
  '.conversation{max-height:none!important;height:auto!important;overflow:visible!important}' +
  '.citation-composer{position:static!important}' });
await settle(800);

const layout = JSON.parse(fs.readFileSync(LAYOUT, 'utf-8'));
await page.screenshot({ path: `${OUT}/wbr-full.png`, fullPage: true });
layout.wbr = { pageH: await page.evaluate(() => document.documentElement.scrollHeight) };

const pieces = await page.$$(
  '.conversation > article.chat-message .chat-author, ' +
  '.conversation > article.chat-message .message-paragraph, ' +
  '.conversation > article.chat-message .tool-receipts summary, ' +
  '.conversation > article.chat-message .source-citation-link',
);
layout.wbr.blocks = [];
for (const p of pieces.slice(0, 20)) {
  const bb = await box(p);
  // 遮罩必须用该块所在消息气泡的真实底色（用户=浅青 / 助手=白）
  const bg = await p.evaluate((e) => {
    const m = e.closest('.chat-message');
    return m ? getComputedStyle(m).backgroundColor : '#ffffff';
  });
  layout.wbr.blocks.push({ ...bb, tag: 'p', bg });
}
console.log('wbr blocks:', layout.wbr.blocks.length);
layout.wbr.leftRail = await box(await page.$('.space-selector'));
layout.wbr.rightRail = await box(await page.$('.buddy-page-grid > aside'));

fs.writeFileSync(LAYOUT, JSON.stringify(layout, null, 1));
console.log('wrote', LAYOUT);
await browser.close();
console.log('CAPTURE V4 DONE');
