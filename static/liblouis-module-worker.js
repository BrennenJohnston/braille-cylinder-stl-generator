/**
 * The liblouis translation worker: liblouis 3.39.0 compiled to WebAssembly
 * (static/vendor/liblouis-3.39.0/) through static/liblouis-engine.js, in a
 * module worker. It replaced the 2017 asm.js 3.2.0 worker in the engine round
 * (plan 05_LIBLOUIS_3_39_UPGRADE_PLAN, 2026-10-09); the messages are the same,
 * and a translation now also reports each cell's input position.
 *
 *   init                                -> { success, message }
 *   translate { text, grade, tableName } -> { success, translation, inputPos }
 *   backTranslate { braille, tableName } -> { success, text }
 *
 * A table and everything it includes (its closure in tables.json) is fetched
 * into the module's file system before its first use, so a table nobody picks
 * is never downloaded. Blank cells come back as the ASCII space (project-facts
 * invariant 4).
 */

import { backTranslate, installTables, loadLiblouis, translate, version } from './liblouis-engine.js';

const VENDOR = '/static/vendor/liblouis-3.39.0/';
// Used only when the caller sends no table name. Contracted UEB matches the
// app's first-run default and BANA's Guidelines for Brailling Business Cards.
const DEFAULT_TABLE = 'en-ueb-g2.ctb';
const G1_TABLE = 'en-ueb-g1.ctb';
const DISPLAY_TABLE = 'unicode.dis';

let mod = null;
let index = null;
const installed = new Set();

async function initialize() {
    mod = await loadLiblouis(() => import(`${VENDOR}liblouis.js`));
    const response = await fetch(`${VENDOR}tables.json`);
    if (!response.ok) throw new Error(`Could not load the table index: HTTP ${response.status}`);
    index = await response.json();
    await ensureTable(DEFAULT_TABLE);
    // One translation proves the engine and the default table work end to end.
    translate(mod, DEFAULT_TABLE, 'test');
    return { success: true, message: `liblouis ${version(mod)} ready` };
}

// The page sends a single table file name; a "unicode.dis,<table>" chain from
// an older caller names the same table.
function tableOf(tableName, grade) {
    if (!tableName) return grade === 'g1' ? G1_TABLE : DEFAULT_TABLE;
    const names = String(tableName).split(',').map((name) => name.trim()).filter((name) => name && name !== DISPLAY_TABLE);
    if (names.length !== 1) throw new Error(`Expected one liblouis table, got: ${tableName}`);
    return names[0];
}

async function ensureTable(table) {
    const closure = index.closures[table];
    if (!closure) throw new Error(`Unknown liblouis table: ${table}`);
    const needed = [...new Set([...index.closures[DISPLAY_TABLE], ...closure])].filter((name) => !installed.has(name));
    const files = await Promise.all(needed.map(async (name) => {
        const response = await fetch(`${VENDOR}tables/${name}`);
        if (!response.ok) throw new Error(`Could not load table ${name}: HTTP ${response.status}`);
        return { name, bytes: new Uint8Array(await response.arrayBuffer()) };
    }));
    installTables(mod, files);
    for (const { name } of files) installed.add(name);
}

function requireReady() {
    if (!mod || !index) throw new Error('Liblouis not initialized');
}

async function handle(type, data) {
    switch (type) {
        case 'init':
            return initialize();
        case 'translate': {
            requireReady();
            const table = tableOf(data.tableName, data.grade);
            await ensureTable(table);
            const { braille, inputPos } = translate(mod, table, data.text);
            if (braille.length === 0) throw new Error(`Translation failed for table ${table}: liblouis returned an empty result`);
            if (![...braille].some((ch) => ch.codePointAt(0) >= 0x2800 && ch.codePointAt(0) <= 0x28ff)) {
                throw new Error(`Translation failed for table ${table}: no braille in the output`);
            }
            return { success: true, translation: braille, inputPos };
        }
        case 'backTranslate': {
            requireReady();
            const table = tableOf(data.tableName);
            await ensureTable(table);
            return { success: true, text: backTranslate(mod, table, data.braille) };
        }
        default:
            throw new Error(`Unknown message type: ${type}`);
    }
}

self.onmessage = async (event) => {
    const { id, type, data } = event.data || {};

    // === SECURITY: Message validation (defense against malformed messages) ===
    const ALLOWED_TYPES = ['init', 'translate', 'backTranslate'];
    if (!type || !ALLOWED_TYPES.includes(type)) {
        self.postMessage({ id, type: 'error', result: { success: false, error: `Invalid message type: ${type}` } });
        return;
    }
    if (id === undefined || id === null) {
        self.postMessage({ type: 'error', result: { success: false, error: 'Missing message id' } });
        return;
    }
    if (type === 'translate') {
        if (!data || typeof data !== 'object') {
            self.postMessage({ id, type, result: { success: false, error: 'Invalid translate data: expected an object' } });
            return;
        }
        if (typeof data.text !== 'string') {
            self.postMessage({ id, type, result: { success: false, error: 'Missing required field: text' } });
            return;
        }
    }
    if (type === 'backTranslate') {
        if (!data || typeof data !== 'object') {
            self.postMessage({ id, type, result: { success: false, error: 'Invalid backTranslate data: expected an object' } });
            return;
        }
        if (typeof data.braille !== 'string') {
            self.postMessage({ id, type, result: { success: false, error: 'Missing required field: braille' } });
            return;
        }
    }
    // === END SECURITY VALIDATION ===

    try {
        self.postMessage({ id, type, result: await handle(type, data) });
    } catch (error) {
        self.postMessage({ id, type, result: { success: false, error: error && error.message ? error.message : String(error) } });
    }
};
