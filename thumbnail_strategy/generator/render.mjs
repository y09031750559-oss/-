import fs from 'fs'; import pw from 'playwright'; import {svg} from './build.mjs'; const {chromium}=pw;
const variants=(await import('./variants.mjs')).default;
const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1280,height:720}});
for(const [name,fn] of Object.entries(variants)){ const base=svg(''); const {html}=svg(fn(base.ukc,base.wc));
 await p.setContent(html); await p.waitForTimeout(300); await p.screenshot({path:`out_${name}.png`}); console.log(name, base.ukc.map(Math.round), base.wc.map(Math.round)); }
await b.close();
