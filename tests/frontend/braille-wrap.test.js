/**
 * Whole-line braille layout (static/braille-wrap.js): a typed line is
 * translated once and cut into rows only at blank cells, and a word longer
 * than a row is divided inside its own braille, with the line continuation
 * sign (dot 5) for an address or a number.
 *
 * The translator is the app's own liblouis 3.39.0 engine
 * (static/liblouis-engine.js on the vendored wasm and tables, contracted UEB,
 * capitals kept), which reports each cell's input position; the expected rows
 * are the ones the 3.2.0 engine's captured translations gave, unchanged by the
 * engine round. A table translator without positions checks the fallback.
 */

// @vitest-environment node
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { beforeAll, describe, it, expect } from 'vitest';
import {
  DIVIDE_AFTER,
  LINE_CONTINUATION,
  continuationNote,
  divideWord,
  layoutParagraph,
  packWords,
  wordKind,
} from '../../static/braille-wrap.js';
import { installTables, loadLiblouis, translate as engineTranslate } from '../../static/liblouis-engine.js';

const VENDOR = new URL('../../static/vendor/liblouis-3.39.0/', import.meta.url);
let engine;

beforeAll(async () => {
  engine = await loadLiblouis(() => import('../../static/vendor/liblouis-3.39.0/liblouis.js'), {
    wasmUrl: fileURLToPath(new URL('liblouis.wasm', VENDOR)),
  });
  const index = JSON.parse(readFileSync(new URL('tables.json', VENDOR), 'utf8'));
  const files = new Set([...index.closures['unicode.dis'], ...index.closures['en-ueb-g2.ctb']]);
  installTables(engine, [...files].map((name) => ({ name, bytes: readFileSync(new URL(`tables/${name}`, VENDOR)) })));
});

/** The real engine: braille and each cell's input position. */
const translate = async (text) => engineTranslate(engine, 'en-ueb-g2.ctb', text);

/** A translator answering only from a table, with no positions. */
const tableTranslator = (table) => async (text) => {
  if (!(text in table)) throw new Error(`no translation for ${JSON.stringify(text)}`);
  return table[text];
};

const brailleRows = (layout) => layout.rows.map((row) => row.braille);

describe('layoutParagraph: whole-line translation', () => {
  it('keeps one capital passage indicator and one terminator over two rows', async () => {
    const layout = await layoutParagraph('ROOM ROOM ROOM ROOM', 13, translate);
    expect(brailleRows(layout)).toEqual(['⠠⠠⠠⠗⠕⠕⠍ ⠗⠕⠕⠍', '⠗⠕⠕⠍ ⠗⠕⠕⠍⠠⠄']);
    expect(layout.rows.map((row) => row.text)).toEqual(['ROOM ROOM', 'ROOM ROOM']);
    // Every cell of the whole line, cut at one blank: 24 cells in all
    expect(brailleRows(layout).join(' ')).toBe((await translate('ROOM ROOM ROOM ROOM')).braille);
    expect(layout.truncated).toBe(false);
  });

  it('joins the words of a row with the ASCII space the request carries', async () => {
    const layout = await layoutParagraph('Hello world', 13, translate);
    expect(brailleRows(layout)).toEqual(['⠠⠓⠑⠇⠇⠕ ⠸⠺']);
    expect(brailleRows(layout)[0]).not.toContain('⠀');
  });

  it('stops at the rows it was given and says the paragraph needs more', async () => {
    const layout = await layoutParagraph('Hello world', 6, translate, 1);
    expect(brailleRows(layout)).toEqual(['⠠⠓⠑⠇⠇⠕']);
    expect(layout.truncated).toBe(true);
  });

  it('gives the paragraph back when typed and braille words do not pair up', async () => {
    const merged = tableTranslator({ 'a b': '⠁⠃' });
    expect(await layoutParagraph('a b', 13, merged)).toBeNull();
  });

  it('pairs words by count when the translator gives no positions', async () => {
    const plain = tableTranslator({ 'Hello world': '⠠⠓⠑⠇⠇⠕ ⠸⠺' });
    const layout = await layoutParagraph('Hello world', 6, plain);
    expect(layout.rows).toEqual([
      { braille: '⠠⠓⠑⠇⠇⠕', text: 'Hello', notes: [] },
      { braille: '⠸⠺', text: 'world', notes: [] },
    ]);
  });
});

describe('layoutParagraph: dividing a word longer than a row', () => {
  it('divides an e-mail address with the line continuation sign, and notes it once', async () => {
    const layout = await layoutParagraph('first.last@example.com', 13, translate);
    expect(brailleRows(layout)).toEqual(['⠋⠊⠗⠌⠲⠇⠁⠌⠈⠁⠐', '⠑⠭⠁⠍⠏⠇⠑⠲⠉⠕⠍']);
    expect(layout.rows.map((row) => row.text)).toEqual(['first.last@', 'example.com']);
    expect(layout.rows.flatMap((row) => row.notes)).toEqual([
      continuationNote('first.last@example.com'),
    ]);
  });

  it('starts the address on its own row after the words before it', async () => {
    const layout = await layoutParagraph('See you at first.last@example.com', 13, translate);
    expect(brailleRows(layout)).toEqual([
      '⠠⠎⠑⠑ ⠽ ⠁⠞',
      '⠋⠊⠗⠌⠲⠇⠁⠌⠈⠁⠐',
      '⠑⠭⠁⠍⠏⠇⠑⠲⠉⠕⠍',
    ]);
  });

  it('keeps ONE number sign across a divided number (UEB 6.10)', async () => {
    const layout = await layoutParagraph('206.555.0147', 8, translate);
    expect(brailleRows(layout)).toEqual(['⠼⠃⠚⠋⠲⠐', '⠑⠑⠑⠲⠚⠁⠙⠛']);
    expect(brailleRows(layout).join('')).toMatch(/^[^⠼]*⠼[^⠼]*$/);
  });

  it('divides a number between the words around it', async () => {
    const layout = await layoutParagraph('Call 206.555.0147 today', 8, translate);
    expect(brailleRows(layout)).toEqual(['⠠⠉⠁⠇⠇', '⠼⠃⠚⠋⠲⠐', '⠑⠑⠑⠲⠚⠁⠙⠛', '⠞⠙']);
    expect(layout.rows.map((row) => row.text)).toEqual(['Call', '206.', '555.0147', 'today']);
  });

  it('divides a long number after a comma, with the sign', async () => {
    const layout = await layoutParagraph('1,000,000,000', 8, translate);
    expect(brailleRows(layout)).toEqual(['⠼⠁⠂⠚⠚⠚⠂⠐', '⠚⠚⠚⠂⠚⠚⠚']);
  });

  it('divides a hyphenated word at the hyphen, with no sign', async () => {
    const layout = await layoutParagraph('self-addressed', 8, translate);
    expect(brailleRows(layout)).toEqual(['⠎⠑⠇⠋⠤', '⠁⠙⠙⠗⠑⠎⠎⠫']);
    expect(layout.rows.flatMap((row) => row.notes)).toEqual([]);
  });

  it('divides a date and words joined by slashes after a slash, with no sign (UEB 7.4.1)', async () => {
    const date = await layoutParagraph('10/31/2026', 8, translate);
    expect(brailleRows(date)).toEqual(['⠼⠁⠚⠸⠌', '⠼⠉⠁⠸⠌', '⠼⠃⠚⠃⠋']);
    const words = await layoutParagraph('schoolchildren/teachers/parents', 13, translate);
    expect(brailleRows(words)).toEqual(['⠎⠡⠕⠕⠇⠡⠊⠇⠙⠗⠢⠸⠌', '⠞⠂⠡⠻⠎⠸⠌⠏⠜⠢⠞⠎']);
    expect([...date.rows, ...words.rows].flatMap((row) => row.notes)).toEqual([]);
  });

  it('uses another row rather than drop the sign', async () => {
    // At 10 cells "first.last@" fills a row with no room for the sign, so the
    // address divides after "first." too, every row but the last signed.
    const layout = await layoutParagraph('first.last@example.com', 10, translate);
    expect(brailleRows(layout)).toEqual(['⠋⠊⠗⠌⠲⠐', '⠇⠁⠌⠈⠁⠐', '⠑⠭⠁⠍⠏⠇⠑⠲⠐', '⠉⠕⠍']);
    expect(layout.rows.map((row) => row.text)).toEqual(['first.', 'last@', 'example.', 'com']);
  });

  it('omits the sign, as a last resort, when a row cannot hold it', async () => {
    // "l." alone gains a grade 1 indicator, so this point is found from the
    // tail's side; the 14-cell middle piece leaves no room for the sign.
    const layout = await layoutParagraph('l.schimmelfennig@usace.army', 14, translate);
    expect(brailleRows(layout)).toEqual(['⠇⠲', '⠎⠡⠊⠍⠍⠑⠇⠋⠢⠝⠊⠛⠈⠁', '⠥⠎⠁⠉⠑⠲⠜⠍⠽']);
    expect(layout.rows.flatMap((row) => row.notes)).toEqual([]);
  });

  it('gives the paragraph back when every piece is still too long for a row', async () => {
    expect(await layoutParagraph('first.last@example.com', 6, translate)).toBeNull();
  });

  it('takes a division point from the cell positions, even where a head alone translates differently', async () => {
    // "first" alone is a whole-word contraction (three cells); inside the
    // address it is spelled out, and the positions still find the point after it.
    const layout = await layoutParagraph('first.last@example.com', 10, translate);
    expect(layout.rows[0]).toEqual({ braille: '⠋⠊⠗⠌⠲⠐', text: 'first.', notes: [continuationNote('first.last@example.com')] });
  });

  it('gives the paragraph back for a word with no division point', async () => {
    expect(await layoutParagraph('bcdfghjklmnpqrstvwxzbcdfghjklm', 13, translate)).toBeNull();
  });
});

describe('the pure parts', () => {
  it('sorts words into addresses, numbers and others', () => {
    expect(wordKind('first.last@example.com')).toBe('address');
    expect(wordKind('www.example.org')).toBe('address');
    expect(wordKind('example.org/visit')).toBe('address');
    expect(wordKind('https://example.org')).toBe('address');
    expect(wordKind('206.555.0147')).toBe('number');
    expect(wordKind('(1,000,000).')).toBe('number');
    expect(wordKind('10/31/2026')).toBe('other');
    expect(wordKind('self-addressed')).toBe('other');
    expect(DIVIDE_AFTER.number).toEqual(['.', ',']);
  });

  it('packs words greedily, one blank cell between them', () => {
    const word = (braille, source, note = null) => ({ braille, cells: braille.length, source, note });
    expect(packWords([word('⠁⠁⠁', 'aaa'), word('⠃⠃', 'bb', 'n'), word('⠉⠉⠉⠉', 'cccc')], 6)).toEqual([
      { braille: '⠁⠁⠁ ⠃⠃', text: 'aaa bb', notes: ['n'] },
      { braille: '⠉⠉⠉⠉', text: 'cccc', notes: [] },
    ]);
  });

  it('divides a word into the longest pieces that fit, counting the sign', () => {
    expect(divideWord(0, 13, [5, 9], 8, 1)).toEqual([[0, 5], [5, 13]]);
    expect(divideWord(0, 13, [5, 9], 8, 0)).toEqual([[0, 5], [5, 13]]);
    expect(divideWord(0, 15, [5, 10], 8, 0)).toEqual([[0, 5], [5, 10], [10, 15]]);
    // A piece longer than a row is kept whole for the caller to refuse
    expect(divideWord(0, 25, [16, 22], 14, 1)).toEqual([[0, 16], [16, 25]]);
  });

  it('names the word in the note, shortened past 40 characters', () => {
    expect(continuationNote('206.555.0147')).toBe(
      '"206.555.0147" is divided across rows. Each row but the last ends with the line continuation sign (dot 5).'
    );
    expect(continuationNote('a'.repeat(45))).toBe(
      `"${'a'.repeat(37)}…" is divided across rows. Each row but the last ends with the line continuation sign (dot 5).`
    );
    expect(LINE_CONTINUATION).toBe('⠐');
  });
});
