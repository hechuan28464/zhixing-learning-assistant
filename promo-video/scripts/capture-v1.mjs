// capture-v1.mjs — 全页 2x 截图，先看真实画面再定切片选择器
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const CHROME = 'C:/Users/HECHUAN/AppData/Local/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-win64/chrome-headless-shell.exe';
const BASE = 'http://127.0.0.1:5174';
const OUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../out/capture');
fs.mkdirSync(OUT, { recursive: true });

const PAGES = [
  { name: 'entry-landing', path: '/' },
  { name: 'entry-examples', path: '/examples' },
  { name: 'entry-guide', path: '/how-it-works' },
  { name: 'home', path: '/app' },
  { name: 'explore', path: '/app?view=explore' },
  { name: 'lesson', path: '/app?view=lesson&lesson=python-condition' },
  { name: 'graph', path: '/app?view=graph' },
  { name: 'reading', path: '/app?view=reading' },
  { name: 'notes', path: '/app?view=notes' },
  { name: 'messages', path: '/app?view=messages' },
  { name: 'projects', path: '/app?view=projects' },
];

const browser = await puppeteer.launch({ executablePath: CHROME, args: ['--no-sandbox', '--force-device-scale-factor=2', '--font-render-hinting=none'] });
const page = await browser.newPage();
await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });

for (const pg of PAGES) {
  await page.goto(BASE + pg.path, { waitUntil: 'networkidle0', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, 900));
  const h = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.screenshot({ path: `${OUT}/${pg.name}-full.png`, fullPage: true });
  console.log(`${pg.name}: pageH=${h}`);
}
await browser.close();
console.log('CAPTURE V1 DONE');
