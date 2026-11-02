// Fixed, reviewed in-container dispatcher. Line-delimited JSON on stdin/stdout.
// Runs INSIDE the network-less sandbox only; never on the host. The host
// re-validates everything and treats these replies as untrusted data.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
const require = createRequire('/opt/repropatch/package.json');

const ROOT = '/workspace/repo';
const DENY = new Set(['.git', 'node_modules', '.env']);
const MAX_READ = 200_000, MAX_OUT = 32_768;
let browser = null, page = null, appProc = null, allowedOrigin = null;

function safe(rel) {
  if (typeof rel !== 'string' || rel.includes('\0') || rel.includes('\\') || path.isAbsolute(rel)) throw new Error('invalid path');
  const parts = rel.split('/').filter(x => x && x !== '.');
  if (parts.includes('..') || parts.some(p => DENY.has(p) || p.startsWith('.env'))) throw new Error('path not allowed');
  let cur = ROOT;
  for (const p of parts) {
    cur = path.join(cur, p);
    let st; try { st = fs.lstatSync(cur); } catch { break; }
    if (st.isSymbolicLink()) throw new Error('symlink not allowed');
  }
  return path.join(ROOT, ...parts);
}

function run(argv, cwd, timeoutMs, env) {
  return new Promise(resolve => {
    const t0 = Date.now();
    let out = '', err = '', done = false, timedOut = false;
    const child = spawn(argv[0], argv.slice(1), {cwd: safe(cwd || '.'), shell: false, detached: true,
      env: {PATH: process.env.PATH, HOME: '/tmp/home', NODE_PATH: process.env.NODE_PATH || '', CI: '1', ...(env || {})}});
    const cap = (s, d) => (s + d).slice(-MAX_OUT * 2);
    child.stdout.on('data', d => out = cap(out, d)); child.stderr.on('data', d => err = cap(err, d));
    const timer = setTimeout(() => { timedOut = true; try { process.kill(-child.pid, 'SIGKILL'); } catch {} }, timeoutMs);
    const fin = code => { if (done) return; done = true; clearTimeout(timer);
      resolve({exit_code: timedOut ? 124 : (code ?? 1), stdout: out.slice(-MAX_OUT), stderr: err.slice(-MAX_OUT), timed_out: timedOut, duration_ms: Date.now() - t0}); };
    child.on('error', e => { err += String(e.message); fin(127); });
    child.on('close', fin);
  });
}

async function ensurePage() {
  if (page) return page;
  if (!allowedOrigin) throw new Error('browser requires serve_start first');
  const {chromium} = require('playwright');
  browser = await chromium.launch({args: ['--no-sandbox', '--disable-dev-shm-usage']});
  const ctx = await browser.newContext({viewport: {width: 1280, height: 800}, acceptDownloads: false, serviceWorkers: 'block'});
  await ctx.route('**/*', r => new URL(r.request().url()).origin === allowedOrigin ? r.continue() : r.abort());
  page = await ctx.newPage();
  await page.goto(allowedOrigin, {timeout:15000});
  return page;
}

async function snapshot(p) {
  const text = await p.evaluate(() => document.body ? document.body.innerText : '');
  return {url: p.url(), title: await p.title(), text: text.slice(0, 6000),
    screenshot_b64: (await p.screenshot({type: 'png', fullPage: false})).toString('base64')};
}

const ops = {
  async list(a) {
    const dir = safe(a.path || '.');
    return {entries: fs.readdirSync(dir, {withFileTypes: true}).filter(e => !DENY.has(e.name) && !e.name.startsWith('.env') && !e.isSymbolicLink())
      .slice(0, 300).map(e => ({name: e.name, type: e.isDirectory() ? 'dir' : 'file'}))};
  },
  async read(a) {
    const f = safe(a.path); const st = fs.lstatSync(f);
    if (!st.isFile() || st.size > MAX_READ) throw new Error('missing file or file exceeds read limit');
    return {content: fs.readFileSync(f, 'utf8')};
  },
  async write(a) {
    const f = safe(a.path);
    if (typeof a.content !== 'string' || Buffer.byteLength(a.content) > 100_000) throw new Error('write exceeds limit');
    fs.mkdirSync(path.dirname(f), {recursive: true}); fs.writeFileSync(f, a.content);
    return {written: true};
  },
  async exec(a) {
    if (!Array.isArray(a.argv) || !a.argv.every(x => typeof x === 'string')) throw new Error('argv required');
    return run(a.argv, a.cwd, Math.min(a.timeout_ms || 60000, 300000), a.env);
  },
  async serve_start(a) {
    const u = new URL(a.url);
    if (!['127.0.0.1', 'localhost'].includes(u.hostname)) throw new Error('loopback only');
    allowedOrigin = u.origin;
    if (appProc) return {started: true, already: true};
    appProc = spawn(a.argv[0], a.argv.slice(1), {cwd: ROOT, shell: false, detached: true, stdio: 'ignore',
      env: {PATH: process.env.PATH, HOME: '/tmp/home', NODE_PATH: process.env.NODE_PATH || ''}});
    const end = Date.now() + Math.min(a.ready_timeout_s || 30, 120) * 1000;
    while (Date.now() < end) {
      try { const r = await fetch(a.url); if (r.status < 500) return {started: true, status: r.status}; } catch {}
      await new Promise(r => setTimeout(r, 300));
    }
    throw new Error('app did not become ready');
  },
  async observe(a) {
    const p = await ensurePage();
    if (a.url) { const u = new URL(a.url, allowedOrigin); if (u.origin !== allowedOrigin) throw new Error('origin not allowed'); await p.goto(u.href, {timeout: 15000}); }
    return snapshot(p);
  },
  async action(a) {
    const p = await ensurePage();
    const t = {timeout: 8000};
    switch (a.kind) {
      case 'click': await p.click(a.selector, t); break;
      case 'fill': await p.fill(a.selector, String(a.value ?? ''), t); break;
      case 'press': await p.press(a.selector || 'body', String(a.value), t); break;
      case 'select': await p.selectOption(a.selector, String(a.value ?? ''), t); break;
      case 'scroll': await p.mouse.wheel(0, Number(a.value) || 400); break;
      case 'wait': await p.waitForTimeout(Math.min(Number(a.value) || 500, 3000)); break;
      default: throw new Error('unknown browser action');
    }
    return snapshot(p);
  },
};

const rl = readline.createInterface({input: process.stdin});
rl.on('line', async line => {
  let msg; try { msg = JSON.parse(line); } catch { return; }
  try {
    if (!Object.hasOwn(ops, msg.op)) throw new Error('unknown op');
    process.stdout.write(JSON.stringify({id: msg.id, ok: true, result: await ops[msg.op](msg)}) + '\n');
  } catch (e) {
    process.stdout.write(JSON.stringify({id: msg.id, ok: false, error: String(e.message || e).slice(0, 500)}) + '\n');
  }
});
rl.on('close', () => process.exit(0));
