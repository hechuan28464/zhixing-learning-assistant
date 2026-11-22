import fs from 'node:fs/promises';import path from 'node:path';
import {bundle} from '@remotion/bundler';import {openBrowser,selectComposition,renderStill} from '@remotion/renderer';
const r=process.cwd(),t=JSON.parse(await fs.readFile('src/timeline.json','utf8'));const out=path.join(r,'out/qa/v2');await fs.mkdir(out,{recursive:true});
const serveUrl=await bundle({entryPoint:path.join(r,'src/index.ts'),publicDir:path.join(r,'public'),onProgress:()=>{}});
const browser=await openBrowser('chrome',{browserExecutable:'C:/Users/HECHUAN/AppData/Local/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-win64/chrome-headless-shell.exe',chromiumOptions:{gl:'angle'},logLevel:'error'});
try{
 const composition=await selectComposition({serveUrl,id:'ZhixingContest',puppeteerInstance:browser,logLevel:'error'});
 const frames=[];
 for(const s of t.shots){for(const [label,frame] of [['enter',s.from+Math.min(70,s.duration-1)],['settled',s.from+Math.round(s.duration*.7)]]){const output=path.join(out,`${s.id}-${label}-${frame}.png`);await renderStill({serveUrl,composition,frame,output,puppeteerInstance:browser,imageFormat:'png',logLevel:'error'});frames.push({shot:s.id,frame,output});}console.log('QA '+s.id);}
 await fs.writeFile(path.join(out,'frames.json'),JSON.stringify(frames,null,2));
}finally{await browser.close({silent:true});}
