// Render each chart page's share images: charts/<id>.png (1200x630 card, also the page's
// share card) and charts/<id>-square.png (1080x1080), both at 2x for print and retina.
// Run after tools/build.py: PLAYWRIGHT_CORE=<path to playwright-core> node tools/render_charts.mjs
// Uses the installed Brave headless; the browser closes when done.
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';
import http from 'http';
import fs from 'fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_CORE || 'playwright-core');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(req.url.split('?')[0].split('#')[0]));
  if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
  res.end(fs.readFileSync(f));
}).listen(0, '127.0.0.1');
await new Promise(r => server.once('listening', r));
const browser = await chromium.launch({
  executablePath: '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser', headless: true });
try {
  const ids = fs.readdirSync(path.join(root, 'charts')).filter(f => f.endsWith('.html')).map(f => f.slice(0, -5));
  for (const id of ids) {
    for (const [mode, w, h, out] of [['card', 1200, 630, `${id}.png`], ['square', 1080, 1080, `${id}-square.png`]]) {
      const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
      await page.goto(`http://127.0.0.1:${server.address().port}/charts/${id}.html#${mode}`);
      await page.waitForFunction(m => document.documentElement.classList.contains(m), mode);
      await page.evaluate(async () => { await document.fonts.ready; });
      const box = await page.locator('.vz').boundingBox();
      if (Math.round(box.width) !== w || Math.round(box.height) !== h) throw new Error(`${id} ${mode}: figure is ${box.width}x${box.height}, want ${w}x${h}`);
      const [sh, ch] = await page.evaluate(() => { const v = document.querySelector('.vz'); return [v.scrollHeight, v.clientHeight]; });
      if (process.env.MEASURE) console.log(id, mode, `content ${sh}px of ${ch}px`);
      else if (sh > ch + 1) throw new Error(`${id} ${mode}: content overflows the image by ${sh - ch}px`);
      // Blocks inside the image must not overlap each other (overflow alone does not catch that).
      const clash = await page.evaluate(() => {
        const parts = [...document.querySelectorAll('.vz-head > *, .vz > *')].filter(el => {
          const cs = getComputedStyle(el), r = el.getBoundingClientRect();
          return cs.display !== 'none' && cs.position !== 'absolute' && r.height > 0 && !el.matches('.vz-head');
        }).map(el => [el.className || el.tagName, el.getBoundingClientRect()]);
        for (let i = 0; i < parts.length; i++) for (let j = i + 1; j < parts.length; j++) {
          const [p, q] = [parts[i][1], parts[j][1]];
          if (p.left < q.right - 1 && q.left < p.right - 1 && p.top < q.bottom - 1 && q.top < p.bottom - 1) return `${parts[i][0]} / ${parts[j][0]}`;
        }
        return '';
      });
      if (clash && !process.env.MEASURE) throw new Error(`${id} ${mode}: overlapping blocks: ${clash}`);
      await page.locator('.vz').screenshot({ path: path.join(root, 'charts', out) });
      await page.close();
      console.log('wrote', `charts/${out}`);
    }
  }
} finally { await browser.close(); server.close(); }
