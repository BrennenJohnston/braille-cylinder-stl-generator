/**
 * Braille ASCII to Unicode braille (static/braille-ascii.js), checked against
 * the North American Braille ASCII Code as liblouis's en-us-brf.dis gives it,
 * read raw from the vendored tables.
 */

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';
import { BRAILLE_ASCII, asciiToCells } from '../../static/braille-ascii.js';

const TABLE = fileURLToPath(
  new URL('../../static/vendor/liblouis-3.39.0/tables/en-us-brf.dis', import.meta.url)
);

/**
 * Each character the table displays and the dots of its cell. The table
 * escapes the backslash as `\\` and the space as `\s`, the blank cell, whose
 * dots it writes as 0.
 */
function readBrfTable() {
  const dots = {};
  for (const line of readFileSync(TABLE, 'utf8').split(/\r?\n/)) {
    const match = /^display\s+(\S+)\s+(\d+)\s*$/.exec(line);
    if (!match) continue;
    const ch = { '\\\\': '\\', '\\s': ' ' }[match[1]] ?? match[1];
    dots[ch] = match[2] === '0' ? '' : match[2];
  }
  return dots;
}

/** The Unicode braille cell with the given dots. */
const cellOf = (dots) =>
  String.fromCharCode(
    0x2800 + [...dots].reduce((bits, dot) => bits | (1 << (dot - 1)), 0)
  );

describe('BRAILLE_ASCII', () => {
  it('puts each character at the index of its cell, as en-us-brf.dis does', () => {
    const table = readBrfTable();
    expect(Object.keys(table)).toHaveLength(64);
    expect(BRAILLE_ASCII).toHaveLength(64);
    for (const [ch, dots] of Object.entries(table)) {
      expect(BRAILLE_ASCII.indexOf(ch)).toBe(cellOf(dots).codePointAt(0) - 0x2800);
    }
  });
});

describe('asciiToCells', () => {
  it('converts the Braille Authority card example h>ry@a"', () => {
    // "harry@" and the line continuation sign, from its card guidelines
    expect(asciiToCells('h>ry@a"')).toEqual({
      text: cellOf('125') + cellOf('345') + cellOf('1235') + cellOf('13456') +
        cellOf('4') + cellOf('1') + cellOf('5'),
      invalid: null,
    });
  });

  it('gives each of the 63 printing characters a distinct cell', () => {
    const table = readBrfTable();
    const printing = Object.keys(table).filter((ch) => ch !== ' ');
    expect(printing).toHaveLength(63);
    const cells = printing.map((ch) => asciiToCells(ch).text);
    expect(new Set(cells).size).toBe(63);
    for (const ch of printing) {
      expect(asciiToCells(ch).text).toBe(cellOf(table[ch]));
    }
  });

  it('keeps a space as the ASCII space, the word separator the request carries', () => {
    // .clinerules/project-facts.md invariant 4: between words the wire
    // carries U+0020, which the braille field and the backend take as one
    // blank cell; U+2800 is not substituted for it.
    expect(asciiToCells('ab cd')).toEqual({
      text: cellOf('1') + cellOf('12') + ' ' + cellOf('14') + cellOf('145'),
      invalid: null,
    });
  });

  it('reads letters in either case as the same cells', () => {
    expect(asciiToCells('hello')).toEqual(asciiToCells('HELLO'));
  });

  it('passes braille cells through and keeps line breaks', () => {
    const cell = cellOf('125');
    expect(asciiToCells(`${cell}a\nb`).text).toBe(
      `${cell}${cellOf('1')}\n${cellOf('12')}`
    );
    expect(asciiToCells('a\r\nb').text).toBe(`${cellOf('1')}\n${cellOf('12')}`);
  });

  it('converts nothing when a character is not braille ASCII, and says where', () => {
    expect(asciiToCells('ab\ncéd')).toEqual({
      text: 'ab\ncéd',
      invalid: { line: 2, char: 'é' },
    });
  });

  it('reads the lowercase NABCC forms as the cells of @ [ \\ ] ^', () => {
    // Some BRF files and braille keyboard programs write these five in
    // lowercase, 0x20 above their uppercase forms, as letters are.
    const pairs = { '`': '@', '{': '[', '|': '\\', '}': ']', '~': '^' };
    for (const [lower, upper] of Object.entries(pairs)) {
      expect(asciiToCells(lower)).toEqual(asciiToCells(upper));
      expect(asciiToCells(lower).invalid).toBeNull();
    }
    expect(asciiToCells('{').text).toBe(cellOf('246'));
  });

  it('accepts every printable ASCII character, so only other characters are refused', () => {
    for (let code = 0x20; code <= 0x7e; code++) {
      expect(asciiToCells(String.fromCharCode(code)).invalid).toBeNull();
    }
    expect(asciiToCells('\t').invalid).toEqual({ line: 1, char: '\t' });
  });
});
