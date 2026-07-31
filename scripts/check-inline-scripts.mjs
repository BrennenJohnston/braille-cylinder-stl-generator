/**
 * Syntax-checks the inline <script> blocks in public/index.html.
 *
 * The app ships as a single HTML file, so a typo in the inline module script
 * only surfaces at runtime in the browser. This extracts each block and parses
 * it so CI (and `node scripts/check-inline-scripts.mjs`) fails fast instead.
 */
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';

const htmlPath = process.argv[2] ?? 'public/index.html';
const html = readFileSync(htmlPath, 'utf8');

const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/gi)];
if (blocks.length === 0) {
  console.error(`No inline scripts found in ${htmlPath}`);
  process.exit(1);
}

const dir = mkdtempSync(join(tmpdir(), 'inline-script-'));
let failures = 0;

blocks.forEach(([, attrs, source], index) => {
  const isModule = /type\s*=\s*["']module["']/i.test(attrs);
  const line = html.slice(0, html.indexOf(source)).split('\n').length;
  const file = join(dir, `block-${index}.${isModule ? 'mjs' : 'js'}`);
  writeFileSync(file, source, 'utf8');
  try {
    execFileSync(process.execPath, ['--check', file], { stdio: 'pipe' });
    console.log(`ok   block ${index} (${isModule ? 'module' : 'classic'}, ~line ${line})`);
  } catch (error) {
    failures += 1;
    console.error(`FAIL block ${index} (${isModule ? 'module' : 'classic'}, ~line ${line})`);
    console.error(String(error.stderr ?? error.message));
  }
});

process.exit(failures === 0 ? 0 : 1);
