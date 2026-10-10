// @vitest-environment node
/**
 * The liblouis 3.39.0 engine (static/liblouis-engine.js) against its vendored
 * WebAssembly build and tables (static/vendor/liblouis-3.39.0/), in Node.
 *
 * The 44 translations captured from today's 3.2.0 worker must come out the
 * same, blank cells as the ASCII space the request carries (project-facts
 * invariant 4), and every cell must report the character it came from. Two
 * texts are known to translate differently on 3.39.0, and are pinned here so
 * the switch-over states them rather than discovers them.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import {
  backTranslate,
  installTables,
  loadLiblouis,
  resetLiblouis,
  translate,
  version,
} from '../../static/liblouis-engine.js';
import captured from './fixtures/ueb-g2-captured-3.2.0.json';

const VENDOR = new URL('../../static/vendor/liblouis-3.39.0/', import.meta.url);
const index = JSON.parse(readFileSync(new URL('tables.json', VENDOR), 'utf8'));
const BLANK = String.fromCharCode(0x2800);

let mod;

beforeAll(async () => {
  resetLiblouis();
  mod = await loadLiblouis(() => import('../../static/vendor/liblouis-3.39.0/liblouis.js'), {
    wasmUrl: fileURLToPath(new URL('liblouis.wasm', VENDOR)),
  });
  const files = new Set([...index.closures['unicode.dis'], ...index.closures['en-ueb-g2.ctb']]);
  installTables(
    mod,
    [...files].map((name) => ({ name, bytes: readFileSync(new URL(`tables/${name}`, VENDOR)) }))
  );
});

afterAll(() => resetLiblouis());

describe('the vendored engine', () => {
  it('is liblouis 3.39.0', () => {
    expect(version(mod)).toBe('3.39.0');
  });

  it('translates every captured 3.2.0 text to the same cells', () => {
    const differences = [];
    for (const [text, braille] of Object.entries(captured)) {
      const now = translate(mod, 'en-ueb-g2.ctb', text).braille;
      if (now !== braille) differences.push(`${text}: ${braille} -> ${now}`);
    }
    expect(differences).toEqual([]);
    expect(Object.keys(captured)).toHaveLength(44);
  });

  it('writes a blank cell as the ASCII space, never U+2800', () => {
    const { braille } = translate(mod, 'en-ueb-g2.ctb', 'ROOM ROOM ROOM ROOM');
    expect(braille).toBe(captured['ROOM ROOM ROOM ROOM']);
    expect(braille.includes(BLANK)).toBe(false);
  });

  it('says which character each cell came from', () => {
    const text = 'first.last@example.com';
    const { braille, inputPos } = translate(mod, 'en-ueb-g2.ctb', text);
    expect(inputPos).toHaveLength([...braille].length);
    expect(inputPos.every((p, i) => p >= 0 && p < text.length && (i === 0 || p >= inputPos[i - 1]))).toBe(true);
    // The @ sign is two cells, both from the @
    const at = text.indexOf('@');
    expect(inputPos.filter((p) => p === at)).toHaveLength(2);
  });

  it('back-translates', () => {
    expect(backTranslate(mod, 'en-ueb-g2.ctb', String.fromCharCode(0x2805))).toBe('knowledge');
    expect(backTranslate(mod, 'en-ueb-g2.ctb', captured['Hello world'])).toBe('Hello world');
  });
});

describe('what 3.39.0 translates differently (the newer engine is the reference)', () => {
  it('numbers separated by a space each take a number sign', () => {
    // 3.2.0 gave the digits after the space dot 5 instead of a number sign.
    expect(translate(mod, 'en-ueb-g2.ctb', 'building 3 100').braille).toBe('⠃⠥⠊⠇⠙⠬ ⠼⠉ ⠼⠁⠚⠚');
  });

  it('two single capital letters are not a capital passage', () => {
    // 3.2.0 opened a capital passage over "A & B".
    expect(translate(mod, 'en-ueb-g2.ctb', 'A & B').braille).toBe('⠠⠁ ⠈⠯ ⠰⠠⠃');
  });
});

describe('the vendored build against native liblouis 3.39.0 (decision E2)', () => {
  const REFERENCE = new URL('../fixtures/liblouis-reference/', import.meta.url);
  const read = (name) => JSON.parse(readFileSync(new URL(name, REFERENCE), 'utf8'));
  const asWire = (braille) => braille.split(BLANK).join(' ');

  it('gives native 3.39.0 cells for the whole English corpus, both grades', () => {
    // corpus.json and english-corpus-3.39.0.json are the forge's (4355e8a),
    // the second written by the native release engine.
    const corpus = read('corpus.json');
    const native = read('english-corpus-3.39.0.json');
    const differences = [];
    for (const [table, rows] of Object.entries(native.tables)) {
      const files = new Set([...index.closures['unicode.dis'], ...index.closures[table]]);
      installTables(mod, [...files].map((name) => ({ name, bytes: readFileSync(new URL(`tables/${name}`, VENDOR)) })));
      for (const { id, text } of corpus) {
        // A row of several lines is translated line by line, as the native
        // reference was (one input line, one output line).
        const now = text
          .split('\n')
          .map((line) => translate(mod, table, line).braille)
          .join('\n');
        if (now !== asWire(rows[id])) differences.push(`${table} ${id}: ${rows[id]} -> ${now}`);
      }
    }
    expect(differences).toEqual([]);
    expect(corpus).toHaveLength(145);
  });

  it('gives native 3.39.0 cells for three samples in every translation table', () => {
    const reference = read('table-samples-3.39.0.json');
    installTables(
      mod,
      Object.keys(index.files).map((name) => ({ name, bytes: readFileSync(new URL(`tables/${name}`, VENDOR)) }))
    );
    const differences = [];
    for (const [table, expected] of Object.entries(reference.tables)) {
      const now = reference.samples.map((sample) => {
        try {
          return translate(mod, table, sample).braille;
        } catch (error) {
          return `ERROR ${error.message}`;
        }
      });
      if (JSON.stringify(now) !== JSON.stringify(expected)) differences.push(`${table}: ${JSON.stringify(now)}`);
    }
    expect(differences).toEqual([]);
    expect(Object.keys(reference.tables)).toHaveLength(323);
  }, 300_000);
});
