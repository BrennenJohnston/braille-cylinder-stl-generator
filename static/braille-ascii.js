/**
 * Braille ASCII, the North American Braille ASCII Code that BRF files and
 * braille keyboard programs use, converted to Unicode braille cells. No DOM.
 *
 * Ported from openscad-assistive-forge src/js/braille-ascii.js (release
 * 5.2.0, 4355e8a), the same author's code, with two changes: a space stays
 * the ASCII space, the word separator the braille field and the request
 * carry (.clinerules/project-facts.md invariant 4), not U+2800; and the
 * lowercase NABCC forms are read as their uppercase cells (Brennen,
 * 2026-10-09), where the forge refuses them.
 */

/**
 * The 64 braille ASCII characters in the order of their cells' dot bits
 * (dot 1 is 1, dot 2 is 2, up to dot 6 at 32), so the character at index n
 * stands for the cell U+2800 + n. The same map as liblouis's en-us-brf.dis.
 */
export const BRAILLE_ASCII =
  ' A1B\'K2L@CIF/MSP"E3H9O6R^DJG>NTQ,*5<-U8V.%[$+X!&;:4\\0Z7(_?W]#Y)=';

const CELL_INDEX = new Map([...BRAILLE_ASCII].map((ch, index) => [ch, index]));

/**
 * Some BRF files and braille keyboard programs write five of the 64 in
 * lowercase, 0x20 above their uppercase forms, the way letters are.
 */
const NABCC_LOWERCASE = new Map([['`', '@'], ['{', '['], ['|', '\\'], ['}', ']'], ['~', '^']]);

const BRAILLE_FIRST = 0x2800;
const BRAILLE_LAST = 0x28ff;

/**
 * Convert braille ASCII to Unicode braille. Letters, and ` { | } ~ for
 * @ [ \ ] ^, may be in either case; Unicode braille cells and spaces pass
 * through and line breaks stay. When
 * any other character is found, nothing is converted.
 * @param {string} text
 * @returns {{ text: string, invalid: { line: number, char: string } | null }}
 *   The converted text; or the text unchanged, with the first character that
 *   is neither braille ASCII nor braille and its line, counted from 1
 */
export function asciiToCells(text) {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const converted = [];
  for (let i = 0; i < lines.length; i++) {
    let cells = '';
    for (const ch of lines[i]) {
      const code = ch.codePointAt(0);
      if (ch === ' ' || (code >= BRAILLE_FIRST && code <= BRAILLE_LAST)) {
        cells += ch;
        continue;
      }
      const upper = /[a-z]/.test(ch) ? ch.toUpperCase() : (NABCC_LOWERCASE.get(ch) ?? ch);
      const index = CELL_INDEX.get(upper);
      if (index === undefined) {
        return { text, invalid: { line: i + 1, char: ch } };
      }
      cells += String.fromCharCode(BRAILLE_FIRST + index);
    }
    converted.push(cells);
  }
  return { text: converted.join('\n'), invalid: null };
}
