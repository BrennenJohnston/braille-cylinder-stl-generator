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
 * The app's liblouis build reports no input positions, so a division point
 * is found by translating the text on each side of it alone: the point is
 * usable when the head's braille is how the word's braille begins, or the
 * tail's braille is how it ends, and both agree when both hold. Whatever
 * this cannot place cleanly - typed and braille words that do not pair up,
 * a long word with no usable point, a piece still longer than a row - is
 * given back (layoutParagraph returns null) for the caller's per-row layout.
 *
 * wordKind, DIVIDE_AFTER, divideWord and the note are ported from
 * openscad-assistive-forge src/js/braille-wrap.js (release 5.2.0, 4355e8a),
 * the same author's code. Words are joined with the ASCII space the request
 * carries (.clinerules/project-facts.md invariant 4).
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
 * Where a word's braille may be cut: for each division character in its
 * typed text, the cell where the text after that character begins.
 * @returns {Promise<Map<number, number>>} Cell index -> typed index
 */
async function divisionPoints(source, braille, divideAfter, translate) {
  const total = cellCount(braille);
  const points = new Map();
  for (let i = 0; i < source.length - 1; i++) {
    if (!divideAfter.includes(source[i])) continue;
    const at = i + 1;
    const head = await translate(source.slice(0, at));
    const tail = await translate(source.slice(at));
    const fromHead = braille.startsWith(head) ? cellCount(head) : null;
    const fromTail = braille.endsWith(tail) ? total - cellCount(tail) : null;
    if (fromHead !== null && fromTail !== null && fromHead !== fromTail) continue;
    const cut = fromHead ?? fromTail;
    if (cut === null || cut <= 0 || cut >= total || points.has(cut)) continue;
    points.set(cut, at);
  }
  return points;
}

/**
 * A word longer than a row, divided in its own braille into pieces that
 * each fit one, or null when it cannot be.
 * @returns {Promise<Array<{ braille: string, cells: number, source: string, note: string|null }>|null>}
 */
async function divideLongWord(source, braille, cols, translate) {
  const kind = wordKind(source);
  const points = await divisionPoints(source, braille, DIVIDE_AFTER[kind], translate);
  if (points.size === 0) return null;
  const cells = [...braille];
  const end = cells.length;
  const cuts = [...points.keys()].sort((a, b) => a - b);
  const overflows = (pieces, signCells) => pieces.some(
    ([from, to], i) => to - from + (i < pieces.length - 1 ? signCells : 0) > cols
  );
  let sign = kind === 'other' ? '' : LINE_CONTINUATION;
  let pieces = divideWord(0, end, cuts, cols, cellCount(sign));
  if (sign && overflows(pieces, cellCount(sign))) {
    sign = '';
    pieces = divideWord(0, end, cuts, cols);
  }
  if (overflows(pieces, cellCount(sign))) return null;
  const typedAt = (cell) => (cell === 0 ? 0 : cell === end ? source.length : points.get(cell));
  return pieces.map(([from, to], i) => {
    const rowSign = i < pieces.length - 1 ? sign : '';
    return {
      braille: cells.slice(from, to).join('') + rowSign,
      cells: to - from + cellCount(rowSign),
      source: source.slice(typedAt(from), typedAt(to)),
      note: i === 0 && sign ? continuationNote(source) : null,
    };
  });
}

/**
 * Lay out one typed line ("paragraph", words separated by single spaces)
 * in rows of at most `cols` cells.
 * @param {string} paragraph
 * @param {number} cols
 * @param {(text: string) => Promise<string>} translate - Typed text to
 *   braille, words separated by ASCII spaces
 * @param {number} [maxRows=Infinity] - Rows wanted at most; a paragraph
 *   needing more comes back cut to this many and marked truncated
 * @returns {Promise<{ rows: Array<{ braille: string, text: string, notes: string[] }>, truncated: boolean }|null>}
 *   Null when the paragraph cannot be laid out from its whole-line braille
 */
export async function layoutParagraph(paragraph, cols, translate, maxRows = Infinity) {
  const typed = paragraph.split(' ');
  const brailleWords = (await translate(paragraph)).split(' ');
  if (brailleWords.length !== typed.length || brailleWords.some((word) => word === '')) {
    return null;
  }
  const words = [];
  for (let k = 0; k < typed.length; k++) {
    const cells = cellCount(brailleWords[k]);
    if (cells <= cols) {
      words.push({ braille: brailleWords[k], cells, source: typed[k], note: null });
      continue;
    }
    const pieces = await divideLongWord(typed[k], brailleWords[k], cols, translate);
    if (!pieces) return null;
    words.push(...pieces);
  }
  const rows = packWords(words, cols);
  return rows.length > maxRows
    ? { rows: rows.slice(0, maxRows), truncated: true }
    : { rows, truncated: false };
}
