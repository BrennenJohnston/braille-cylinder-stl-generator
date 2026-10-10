/**
 * Whole-line braille layout for Auto Placement. Each typed line is
 * translated once, whole, and its braille is cut into rows only at blank
 * cells, so an indicator that spans words keeps its one opening and one
 * closing sign (a capital passage over rows, UEB 8.5.7). A word longer than
 * a row is divided inside its own braille, never translated again: an
 * e-mail or web address after @ . - / : _ and a number after a period or
 * comma, each row but the last ending with the line continuation sign, dot 5
 * (BANA's business card guidelines; UEB 6.10 keeps one number sign across
 * the division); any other word after . - / : with no sign, as a hyphen or
 * a slash already ends its row (UEB 10.13.2, 7.4.1). When the sign does not
 * fit on every row the word divides without it, the guidelines' last resort.
 * No DOM.
 *
 * liblouis 3.39.0 reports, for each cell, the typed character it came from
 * (lou_translate's input positions), so each braille word's typed text and
 * the cells a word may be divided at come from those positions, as in the
 * forge (the engine round, decision E4, 2026-10-09; until then the 3.2.0
 * engine had none, and each division point was found by translating the
 * text on either side of it alone). A translator that answers with the
 * braille alone pairs braille and typed words by count. Whatever this cannot
 * place cleanly - words that do not pair up, a long word with no division
 * point, a piece still longer than a row - is given back (layoutParagraph
 * returns null) for the caller's per-row layout.
 *
 * wordKind, DIVIDE_AFTER, wordRanges, divisionPoints, divideWord and the note
 * are ported from openscad-assistive-forge src/js/braille-wrap.js (release
 * 5.2.0, 4355e8a), the same author's code. Words are joined with the ASCII
 * space the request carries (.clinerules/project-facts.md invariant 4).
 */

/** The line continuation sign (dot 5). */
export const LINE_CONTINUATION = '⠐';

/** Characters after which an over-long word of each kind may be divided. */
export const DIVIDE_AFTER = {
  address: ['@', '.', '-', '/', ':', '_'],
  number: ['.', ','],
  other: ['.', '-', '/', ':'],
};

const cellCount = (braille) => [...braille].length;

/**
 * The kind of a word's typed text, for dividing it. A slash alone does not
 * make an address: words joined by a slash, and dates, divide after it with
 * no sign (UEB 7.4.1); it counts after a domain name, as in example.org/visit.
 * @param {string} source
 * @returns {'address'|'number'|'other'}
 */
export function wordKind(source) {
  const core = source.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
  if (/@|:\/\/|^www\./i.test(core) || /^[^/]*\.\p{L}[^/]*\//u.test(core)) {
    return 'address';
  }
  if (/^\d+(?:[.,]\d+)+$/.test(core)) return 'number';
  return 'other';
}

/**
 * The note shown once for each word divided with the line continuation sign.
 * @param {string} source - The word's typed text
 * @returns {string}
 */
export function continuationNote(source) {
  const word = source.length > 40 ? `${source.slice(0, 37)}…` : source;
  return `"${word}" is divided across rows. Each row but the last ends with ` +
    'the line continuation sign (dot 5).';
}

/**
 * Greedily pack words into rows of at most `cols` cells, breaking only
 * between words, one blank cell (an ASCII space) between them.
 * @param {Array<{ braille: string, cells: number, source: string, note?: string|null }>} words
 * @param {number} cols
 * @returns {Array<{ braille: string, text: string, notes: string[] }>} Each
 *   row's braille, its typed words, and the notes of the words it holds
 */
export function packWords(words, cols) {
  const rows = [];
  let row = null;
  for (const word of words) {
    if (row && row.cells + 1 + word.cells <= cols) {
      row.braille += ' ' + word.braille;
      row.cells += 1 + word.cells;
      row.sources.push(word.source);
    } else {
      if (row) rows.push(row);
      row = { braille: word.braille, cells: word.cells, sources: [word.source], notes: [] };
    }
    if (word.note) row.notes.push(word.note);
  }
  if (row) rows.push(row);
  return rows.map(({ braille, sources, notes }) => ({ braille, text: sources.join(' '), notes }));
}

/**
 * Group a word's cells into pieces that each fill a line, cutting only at
 * division points. Every piece but the last is followed by `signCells` more
 * cells, which its line must hold too. A piece longer than a line is kept
 * whole.
 * @returns {Array<[number, number]>} [start, end) cell ranges
 */
export function divideWord(start, end, points, cellsPerLine, signCells = 0) {
  const pieces = [];
  let pieceStart = start;
  let lastFit = start;
  const fits = (cut) =>
    cut - pieceStart + (cut === end ? 0 : signCells) <= cellsPerLine;
  for (const cut of [...points, end]) {
    if (fits(cut)) {
      lastFit = cut;
      continue;
    }
    if (lastFit > pieceStart) {
      pieces.push([pieceStart, lastFit]);
      pieceStart = lastFit;
    }
    if (fits(cut)) {
      lastFit = cut;
      continue;
    }
    pieces.push([pieceStart, cut]);
    pieceStart = cut;
    lastFit = cut;
  }
  if (lastFit > pieceStart) pieces.push([pieceStart, lastFit]);
  return pieces;
}

/**
 * A translator may answer with `{ braille, inputPos }` or with the braille
 * alone; positions are used only when there is one for every cell.
 * @param {string|{ braille: string, inputPos?: number[]|null }} answer
 * @returns {{ braille: string, inputPos: number[]|null }}
 */
function asTranslation(answer) {
  if (typeof answer === 'string') return { braille: answer, inputPos: null };
  const braille = String(answer.braille);
  const inputPos = Array.isArray(answer.inputPos) && answer.inputPos.length === cellCount(braille)
    ? answer.inputPos
    : null;
  return { braille, inputPos };
}

/**
 * The braille words of a translated line: [start, end) cell ranges between
 * blank cells.
 * @param {string[]} cells
 * @returns {Array<[number, number]>}
 */
function wordSpans(cells) {
  const spans = [];
  let start = -1;
  cells.forEach((cell, i) => {
    if (cell === ' ') {
      if (start >= 0) spans.push([start, i]);
      start = -1;
    } else if (start < 0) {
      start = i;
    }
  });
  if (start >= 0) spans.push([start, cells.length]);
  return spans;
}

/**
 * Where each braille word's typed text lies in the line: from the character
 * its first cell came from to the next word's (the first word from the
 * line's start, the last to its end). Null when the positions do not run
 * forward from word to word.
 * @returns {Array<[number, number]>|null}
 */
function wordRanges(line, spans, inputPos) {
  const starts = spans.map(([start]) => inputPos[start]);
  if (starts.some((p, k) => k > 0 && !(p > starts[k - 1]))) return null;
  return starts.map((p, k) => [k === 0 ? 0 : p, starts[k + 1] ?? line.length]);
}

/**
 * The same ranges from the typed words, for a translator without positions:
 * only when there are as many braille words as typed ones.
 * @returns {Array<[number, number]>|null}
 */
function rangesByCount(line, spans) {
  const typed = line.split(' ');
  if (typed.length !== spans.length) return null;
  let at = 0;
  return typed.map((word) => {
    const range = [at, at + word.length];
    at += word.length + 1;
    return range;
  });
}

/**
 * Cells of a braille word at which a new row may start: the first cell past
 * each of `divideAfter` in the word's typed text.
 * @returns {number[]} Cell indexes, ascending, inside (start, end)
 */
function divisionPoints(line, inputPos, start, end, divideAfter) {
  const points = new Set();
  for (let i = start; i < end; i++) {
    if (!divideAfter.includes(line[inputPos[i]])) continue;
    let j = i + 1;
    while (j < end && inputPos[j] <= inputPos[i]) j++;
    if (j < end) points.add(j);
  }
  return [...points].sort((a, b) => a - b);
}

/**
 * A word longer than a row, divided in its own braille into pieces that
 * each fit one, or null when it cannot be.
 * @returns {Array<{ braille: string, cells: number, source: string, note: string|null }>|null}
 */
function divideLongWord(line, cells, inputPos, [start, end], [wordFrom, wordTo], cols) {
  const source = line.slice(wordFrom, wordTo).trim();
  const kind = wordKind(source);
  const points = divisionPoints(line, inputPos, start, end, DIVIDE_AFTER[kind]);
  if (points.length === 0) return null;
  const overflows = (pieces, signCells) => pieces.some(
    ([from, to], i) => to - from + (i < pieces.length - 1 ? signCells : 0) > cols
  );
  let sign = kind === 'other' ? '' : LINE_CONTINUATION;
  let pieces = divideWord(start, end, points, cols, cellCount(sign));
  if (sign && overflows(pieces, cellCount(sign))) {
    sign = '';
    pieces = divideWord(start, end, points, cols);
  }
  if (overflows(pieces, cellCount(sign))) return null;
  return pieces.map(([from, to], i) => {
    const rowSign = i < pieces.length - 1 ? sign : '';
    const textFrom = from === start ? wordFrom : inputPos[from];
    const textTo = to === end ? wordTo : inputPos[to];
    return {
      braille: cells.slice(from, to).join('') + rowSign,
      cells: to - from + cellCount(rowSign),
      source: line.slice(textFrom, textTo).trim(),
      note: i === 0 && sign ? continuationNote(source) : null,
    };
  });
}

/**
 * Lay out one typed line ("paragraph", words separated by single spaces)
 * in rows of at most `cols` cells.
 * @param {string} paragraph
 * @param {number} cols
 * @param {(text: string) => Promise<string|{ braille: string, inputPos: number[] }>} translate -
 *   Typed text to braille, words separated by ASCII spaces, ideally with
 *   each cell's position in the text
 * @param {number} [maxRows=Infinity] - Rows wanted at most; a paragraph
 *   needing more comes back cut to this many and marked truncated
 * @returns {Promise<{ rows: Array<{ braille: string, text: string, notes: string[] }>, truncated: boolean }|null>}
 *   Null when the paragraph cannot be laid out from its whole-line braille
 */
export async function layoutParagraph(paragraph, cols, translate, maxRows = Infinity) {
  const { braille, inputPos } = asTranslation(await translate(paragraph));
  const cells = [...braille];
  const spans = wordSpans(cells);
  const ranges = (inputPos && wordRanges(paragraph, spans, inputPos)) || rangesByCount(paragraph, spans);
  if (!ranges || spans.length === 0) return null;
  const words = [];
  for (let k = 0; k < spans.length; k++) {
    const [start, end] = spans[k];
    if (end - start <= cols) {
      const [from, to] = ranges[k];
      words.push({ braille: cells.slice(start, end).join(''), cells: end - start, source: paragraph.slice(from, to).trim(), note: null });
      continue;
    }
    const pieces = inputPos && divideLongWord(paragraph, cells, inputPos, spans[k], ranges[k], cols);
    if (!pieces) return null;
    words.push(...pieces);
  }
  const rows = packWords(words, cols);
  return rows.length > maxRows
    ? { rows: rows.slice(0, maxRows), truncated: true }
    : { rows, truncated: false };
}
