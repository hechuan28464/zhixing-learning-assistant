// capture-v2.mjs — 产出与 Ink Press 场景契约严格对齐的三件套
//   textures: projects-full / projects-empty / card1..6 / card4-hires / nav /
//             float-search / float-stats / detail-full / papers-full /
//             paper1..5 / wbr-full
//   layout:   src/aifl/live-layout.json 的 projects/detail/papers/wbr 四个 key
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const CHROME = 'C:/Users/HECHUAN/AppData/Local/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-win64/chrome-headless-shell.exe';
const BASE = 'http://127.0.0.1:5174';
const HERE = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(HERE, '../public/textures/live');
const LAYOUT = path.resolve(HERE, '../src/aifl/live-layout.json');
fs.mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME,
  args: ['--no-sandbox', '--force-device-scale-factor=2', '--font-render-hinting=none'],
});
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });

const settle = async (ms = 900) => {
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, ms));
};
const box = (el) =>
  el.evaluate((e) => {
    const r = e.getBoundingClientRect();
    return { x: r.x + window.scrollX, y: r.y + window.scrollY, w: r.width, h: r.height };
  });

const layout = { pageW: 1920 };

// ---------------- A. 课程广场 -> projects ----------------
await page.goto(BASE + '/app?view=explore', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1200);
layout.projects = { pageH: await page.evaluate(() => document.documentElement.scrollHeight) };

const topbar = await page.$('.topbar');
layout.projects.header = await box(topbar);

const pills = await page.$$('.course-gallery-toolbar .studio-pills > button');
layout.projects.sections = [];
for (const p of pills) {
  const b = await box(p);
  const text = await p.evaluate((e) => e.textContent.trim());
  layout.projects.sections.push({ text, ...b });
}

// 卡片顺序：3 个方向按钮在前，编程课卡落在 index 3（SceneOpen 的 MAIN=3 主角）
const articles = await page.$$('.course-gallery-cards > article');
const byTitle = async (el) => el.evaluate((e) => (e.querySelector('h2')?.textContent || '').trim());
const artMap = {};
for (const a of articles) artMap[(await byTitle(a)).slice(0, 4)] = a;
const insps = await page.$$('.course-inspiration-strip button');
const ordered = [insps[0], insps[1], insps[2], artMap['Pyth'], artMap['从问题到'], artMap['在阅读中']];

layout.projects.cards = [];
for (let i = 0; i < ordered.length; i++) {
  const el = ordered[i];
  const b = await box(el);
  const file = `card${i + 1}.png`;
  await el.screenshot({ path: `${OUT}/${file}` });
  layout.projects.cards.push({ file, ...b, title: await byTitle(el) });
  console.log('card', i + 1, layout.projects.cards[i].title, b);
}

await page.screenshot({ path: `${OUT}/projects-full.png`, fullPage: true });
await page.evaluate(() => {
  document.querySelectorAll('.course-gallery-cards > article, .course-inspiration-strip button')
    .forEach((el) => { el.style.visibility = 'hidden'; });
});
await settle(300);
await page.screenshot({ path: `${OUT}/projects-empty.png`, fullPage: true });
await page.evaluate(() => {
  document.querySelectorAll('.course-gallery-cards > article, .course-inspiration-strip button')
    .forEach((el) => { el.style.visibility = ''; });
});

// nav / float-search 取自顶栏
await (await page.$('.topbar')).screenshot({ path: `${OUT}/nav.png` });
const searchInput = await page.$('.topbar input');
const searchWrap = await searchInput.evaluateHandle((e) => e.closest('form') || e.parentElement);
await searchWrap.asElement().screenshot({ path: `${OUT}/float-search.png`, omitBackground: true });
layout.search = await box(searchWrap.asElement());

// card4-hires：主角卡 4x
const page4 = await browser.newPage();
await page4.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 4 });
await page4.goto(BASE + '/app?view=explore', { waitUntil: 'networkidle0', timeout: 60000 });
await page4.evaluate(() => document.fonts.ready);
await new Promise((r) => setTimeout(r, 900));
const arts4 = await page4.$$('.course-gallery-cards > article');
for (const a of arts4) {
  const t = await a.evaluate((e) => (e.querySelector('h2')?.textContent || '').trim());
  if (t.startsWith('Python')) { await a.screenshot({ path: `${OUT}/card4-hires.png` }); console.log('card4-hires ok'); }
}
await page4.close();

// ---------------- B. 学习工作台 -> detail ----------------
await page.goto(BASE + '/app?view=learning', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1000);
const clicked = await page.evaluate(() => {
  const card = [...document.querySelectorAll('.course-card')].find((e) => /Python/.test(e.textContent || ''));
  if (card) { card.click(); return true; }
  return false;
});
console.log('clicked python course card:', clicked);
await settle(1500);
await page.screenshot({ path: `${OUT}/detail-full.png`, fullPage: true });
layout.detail = { pageH: await page.evaluate(() => document.documentElement.scrollHeight) };
const evRows = await page.$$('.evidence-four > article');
layout.detail.rows = [];
for (const r of evRows) layout.detail.rows.push(await box(r));
console.log('evidence rows:', layout.detail.rows.length);

// ---------------- C. 学习动态 -> papers ----------------
await page.goto(BASE + '/app?view=messages', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1200);
await page.screenshot({ path: `${OUT}/papers-full.png`, fullPage: true });
layout.papers = { pageH: await page.evaluate(() => document.documentElement.scrollHeight) };
const events = await page.$$('.learning-timeline > article');
layout.papers.cards = [];
for (let i = 0; i < Math.min(5, events.length); i++) {
  const b = await box(events[i]);
  const file = `paper${i + 1}.png`;
  await events[i].screenshot({ path: `${OUT}/${file}` });
  layout.papers.cards.push(b);
  console.log('paper', i + 1, b);
}

// ---------------- D. 学习示例 -> wbr ----------------
await page.goto(BASE + '/examples', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1200);
await page.screenshot({ path: `${OUT}/wbr-full.png`, fullPage: true });
layout.wbr = { pageH: await page.evaluate(() => document.documentElement.scrollHeight) };
const blockSel = '.entry-tab-body header h2, .entry-tab-body header span, .entry-question-strip, ' +
  '.entry-tab-body > p, .entry-example-equations, .entry-takeaway, .entry-sample-question, ' +
  '.entry-example-actions, .entry-source-detail';
const blocks = await page.$$(blockSel);
layout.wbr.blocks = [];
for (const b of blocks.slice(0, 20)) {
  const bb = await box(b);
  const tag = await b.evaluate((e) => e.tagName.toLowerCase());
  layout.wbr.blocks.push({ ...bb, tag: tag === 'h2' ? 'h2' : tag === 'h3' ? 'h2' : 'p' });
}
console.log('wbr blocks:', layout.wbr.blocks.length);
layout.wbr.leftRail = await box(await page.$('.entry-example-selector'));
layout.wbr.rightRail = await box(await page.$('.entry-sample-question'));

// ---------------- E. float-stats 取自首页课程卡脚 ----------------
await page.goto(BASE + '/app', { waitUntil: 'networkidle0', timeout: 60000 });
await settle(1000);
const footer = await page.$('.course-card .course-footer');
await footer.screenshot({ path: `${OUT}/float-stats.png`, omitBackground: true });
layout.stats = await box(footer);

fs.writeFileSync(LAYOUT, JSON.stringify(layout, null, 1));
console.log('wrote', LAYOUT);
await browser.close();
console.log('CAPTURE V2 DONE');
