// capture-v5.mjs — 带登录态重截 explore/detail/messages/home 素材，统一顶栏连续性。
// 不碰 layout.wbr（buddy 真实对话页由 capture-v4 负责）。
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

await page.goto(BASE + '/app', { waitUntil: 'networkidle0', timeout: 60000 });
console.log('login:', await page.evaluate(async () => {
  const r = await fetch('/api/auth/login', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'demo', password: 'promo-demo-2026', remember: false }),
  });
  return r.status;
}));

const layout = JSON.parse(fs.readFileSync(LAYOUT, 'utf-8'));

// ---- explore ----
await page.goto(BASE + '/app?view=explore', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1200);
layout.projects.pageH = await page.evaluate(() => document.documentElement.scrollHeight);
layout.projects.header = await box(await page.$('.topbar'));
layout.projects.sections = [];
for (const p of await page.$$('.course-gallery-toolbar .studio-pills > button')) {
  layout.projects.sections.push({ text: await p.evaluate((e) => e.textContent.trim()), ...(await box(p)) });
}
const articles = await page.$$('.course-gallery-cards > article');
const byTitle = async (el) => el.evaluate((e) => (e.querySelector('h2')?.textContent || '').trim());
const artMap = {};
for (const a of articles) artMap[(await byTitle(a)).slice(0, 4)] = a;
const insps = await page.$$('.course-inspiration-strip button');
const ordered = [insps[0], insps[1], insps[2], artMap['Pyth'], artMap['从问题到'], artMap['在阅读中']];
layout.projects.cards = [];
for (let i = 0; i < ordered.length; i++) {
  const b = await box(ordered[i]);
  const file = `card${i + 1}.png`;
  await ordered[i].screenshot({ path: `${OUT}/${file}` });
  layout.projects.cards.push({ file, ...b, title: await byTitle(ordered[i]) });
}
await page.screenshot({ path: `${OUT}/projects-full.png`, fullPage: true });
await page.evaluate(() => {
  document.querySelectorAll('.course-gallery-cards > article, .course-inspiration-strip button')
    .forEach((el) => { el.style.visibility = 'hidden'; });
});
await settle(300);
await page.screenshot({ path: `${OUT}/projects-empty.png`, fullPage: true });
await (await page.$('.topbar')).screenshot({ path: `${OUT}/nav.png` });
const sw = await (await page.$('.topbar input')).evaluateHandle((e) => e.closest('form') || e.parentElement);
await sw.asElement().screenshot({ path: `${OUT}/float-search.png`, omitBackground: true });
layout.search = await box(sw.asElement());

const page4 = await browser.newPage();
await page4.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 4 });
await page4.goto(BASE + '/app?view=explore', { waitUntil: 'networkidle0', timeout: 60000 });
await page4.evaluate(() => document.fonts.ready);
await new Promise((r) => setTimeout(r, 900));
for (const a of await page4.$$('.course-gallery-cards > article')) {
  const t = await a.evaluate((e) => (e.querySelector('h2')?.textContent || '').trim());
  if (t.startsWith('Python')) await a.screenshot({ path: `${OUT}/card4-hires.png` });
}
await page4.close();

// ---- detail ----
await page.goto(BASE + '/app?view=learning', { waitUntil: 'networkidle0', timeout: 60000 });
await settle();
await page.evaluate(() => {
  const row = [...document.querySelectorAll('.learning-recent-row')].find((e) => /Python/.test(e.textContent || ''));
  if (row) row.click();
});
await settle(1600);
await page.screenshot({ path: `${OUT}/detail-full.png`, fullPage: true });
layout.detail = { pageH: await page.evaluate(() => document.documentElement.scrollHeight), rows: [] };
for (const r of await page.$$('.evidence-four > article')) layout.detail.rows.push(await box(r));
console.log('detail rows:', layout.detail.rows.length);

// ---- papers ----
await page.goto(BASE + '/app?view=messages', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1200);
await page.screenshot({ path: `${OUT}/papers-full.png`, fullPage: true });
layout.papers = { pageH: await page.evaluate(() => document.documentElement.scrollHeight), cards: [] };
const events = await page.$$('.learning-timeline > article');
for (let i = 0; i < Math.min(5, events.length); i++) {
  await events[i].screenshot({ path: `${OUT}/paper${i + 1}.png` });
  layout.papers.cards.push(await box(events[i]));
}

// ---- float-stats ----
await page.goto(BASE + '/app', { waitUntil: 'networkidle0', timeout: 60000 });
await settle();
const footer = await page.$('.course-card .course-footer');
await footer.screenshot({ path: `${OUT}/float-stats.png`, omitBackground: true });
layout.stats = await box(footer);

fs.writeFileSync(LAYOUT, JSON.stringify(layout, null, 1));
console.log('wrote', LAYOUT);
await browser.close();
console.log('CAPTURE V5 DONE');
