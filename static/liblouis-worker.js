// Web Worker for liblouis translation
// This allows us to use enableOnDemandTableLoading which only works in web workers

let liblouisInstance = null;
let liblouisReady = false;
let recentLogs = [];

// Used only when the caller sends no table name. Contracted UEB matches the
// app's first-run default and BANA's Guidelines for Brailling Business Cards.
const DEFAULT_TABLE = 'en-ueb-g2.ctb';

// Import liblouis scripts with error handling
try {
    console.log('Worker: Attempting to load liblouis scripts from static directory...');
    importScripts('/static/liblouis/build-no-tables-utf16.js');
    console.log('Worker: Loaded build-no-tables-utf16.js');
    importScripts('/static/liblouis/easy-api.js');
    console.log('Worker: Loaded easy-api.js');
} catch (error) {
    console.error('Worker: Failed to load liblouis scripts from static:', error);
    // Try original paths as fallback
    try {
        console.log('Worker: Trying original node_modules paths...');
        importScripts('/node_modules/liblouis-build/build-no-tables-utf16.js');
        importScripts('/node_modules/liblouis/easy-api.js');
        console.log('Worker: Loaded scripts with node_modules paths');
    } catch (altError) {
        console.error('Worker: All paths failed:', altError);
        throw new Error('Could not load liblouis scripts: ' + error.message);
    }
}

// Initialize liblouis in the worker
async function initializeLiblouis() {
    try {
        console.log('Worker: Initializing liblouis...');
        
        // Wait for scripts to load
        await new Promise(resolve => setTimeout(resolve, 100));
        
        if (typeof liblouisBuild !== 'undefined' && typeof LiblouisEasyApi !== 'undefined') {
            console.log('Worker: Creating LiblouisEasyApi instance');
            liblouisInstance = new LiblouisEasyApi(liblouisBuild);

            try {
                liblouisInstance.registerLogCallback(function(level, msg){
                    try {
                        recentLogs.push(`[${level}] ${msg}`);
                        if (recentLogs.length > 50) {
                            recentLogs.shift();
                        }
                    } catch (_) {}
                });
            } catch (_) {}
            
            // Enable on-demand table loading - this should work in web worker
            if (liblouisInstance.enableOnDemandTableLoading) {
                console.log('Worker: Enabling on-demand table loading...');
                try {
                    // Prefer absolute origin-based URL for robustness on Vercel/CDN
                    var origin = (self && self.location && self.location.origin) ? self.location.origin : '';
                    var tableBase = origin + '/static/liblouis/tables/';
                    // Try the absolute static directory first
                    liblouisInstance.enableOnDemandTableLoading(tableBase);
                    console.log('Worker: Table loading enabled from static directory');
                } catch (e) {
                    console.log('Worker: Static path failed, trying node_modules path...');
                    try {
                        liblouisInstance.enableOnDemandTableLoading('/node_modules/liblouis-build/tables/');
                        console.log('Worker: Table loading enabled from node_modules');
                    } catch (e2) {
                        console.log('Worker: Both paths failed, trying relative path...');
                        try {
                            liblouisInstance.enableOnDemandTableLoading('static/liblouis/tables/');
                            console.log('Worker: Table loading enabled with relative path');
                        } catch (e3) {
                            console.log('Worker: All table loading attempts failed:', e3.message);
                            // Continue without on-demand loading - tables might be pre-loaded
                        }
                    }
                }
            } else {
                console.log('Worker: enableOnDemandTableLoading not available, tables may be pre-loaded');
            }

            // Do NOT set an absolute URL as data path: liblouis expects a virtual FS path.
            // Rely on enableOnDemandTableLoading to fetch tables over HTTP.
            try {
                if (liblouisInstance.setDataPath) {
                    liblouisInstance.setDataPath('');
                    console.log('Worker: Data path cleared (using dynamic loader)');
                }
            } catch (e) {
                console.log('Worker: setDataPath adjustment failed:', e && e.message ? e.message : e);
            }
            
            liblouisReady = true;
            console.log('Worker: Liblouis initialized successfully');
            
            // Preload core tables to help include resolution in some environments
            try { liblouisInstance.loadTable('unicode.dis'); } catch (_) {}
            try { liblouisInstance.loadTable('en-ueb-g1.ctb'); } catch (_) {}
            try { liblouisInstance.loadTable('en-ueb-g2.ctb'); } catch (_) {}
            try { liblouisInstance.loadTable('en-ueb-math.ctb'); } catch (_) {}

            // Test translation to verify it works (check UEB tables specifically)
            try {
                const ok = liblouisInstance.checkTable('unicode.dis,en-ueb-g1.ctb');
                console.log('Worker: checkTable unicode.dis,en-ueb-g1.ctb =>', ok);
            } catch (_) {}
            try {
                const testResult = liblouisInstance.translateString('unicode.dis,en-ueb-g1.ctb', 'test');
                console.log('Worker: Test translation attempt (UEB g1):', testResult);
            } catch (e) {
                console.log('Worker: Test translation failed (UEB g1):', e.message);
            }
            
            return { success: true, message: 'Liblouis initialized successfully' };
        } else {
            throw new Error('Liblouis scripts not loaded properly');
        }
    } catch (error) {
        console.error('Worker: Failed to initialize liblouis:', error);
        return { success: false, error: error.message };
    }
}

// Handle messages from main thread
self.onmessage = async function(e) {
    const { id, type, data } = e.data;

    // === SECURITY: Message validation (defense against malformed messages) ===
    // Allowlist of valid message types
    const ALLOWED_TYPES = ['init', 'translate', 'backTranslate'];
    if (!type || !ALLOWED_TYPES.includes(type)) {
        self.postMessage({
            id: id,
            type: 'error',
            result: { success: false, error: 'Invalid message type: ' + type }
        });
        return;
    }

    // Validate message id exists
    if (id === undefined || id === null) {
        self.postMessage({
            type: 'error',
            result: { success: false, error: 'Missing message id' }
        });
        return;
    }

    // For 'translate' type, validate data object structure
    if (type === 'translate') {
        if (!data || typeof data !== 'object') {
            self.postMessage({
                id: id,
                type: 'translate',
                result: { success: false, error: 'Invalid translate data: expected an object' }
            });
            return;
        }
        if (!data.text && data.text !== '') {
            self.postMessage({
                id: id,
                type: 'translate',
                result: { success: false, error: 'Missing required field: text' }
            });
            return;
        }
    }

    // For 'backTranslate' type, the payload carries braille instead of text
    if (type === 'backTranslate') {
        if (!data || typeof data !== 'object') {
            self.postMessage({
                id: id,
                type: 'backTranslate',
                result: { success: false, error: 'Invalid backTranslate data: expected an object' }
            });
            return;
        }
        if (typeof data.braille !== 'string') {
            self.postMessage({
                id: id,
                type: 'backTranslate',
                result: { success: false, error: 'Missing required field: braille' }
            });
            return;
        }
    }
    // === END SECURITY VALIDATION ===

    try {
        switch (type) {
            case 'init':
                const initResult = await initializeLiblouis();
                self.postMessage({ id, type: 'init', result: initResult });
                break;
                
            case 'translate':
                if (!liblouisReady || !liblouisInstance) {
                    throw new Error('Liblouis not initialized');
                }
                
                const { text, grade, tableName } = data;
                
                // Use the provided table name or default UEB based on grade when not specified
                let selectedTable;
                if (tableName) {
                    selectedTable = tableName;
                } else {
                    selectedTable = grade === 'g1' ? 'en-ueb-g1.ctb' : DEFAULT_TABLE;
                }

                console.log('Worker: Translating text:', text, 'with table:', selectedTable);

                try {
                    // Ensure unicode braille output by adding unicode-braille.utb to the table chain
                    // Use unicode.dis as first table to force Unicode Braille output
                    const tableChain = selectedTable.indexOf('unicode.dis') !== -1
                        ? selectedTable
                        : ('unicode.dis,' + selectedTable);
                    const result = liblouisInstance.translateString(tableChain, text);
                    if (typeof result !== 'string' || result.length === 0) {
                        throw new Error('Liblouis returned empty result');
                    }
                    const hasBrailleChars = result.split('').some(function(char){
                        const code = char.charCodeAt(0);
                        return code >= 0x2800 && code <= 0x28FF;
                    });
                    if (!hasBrailleChars) {
                        throw new Error('Translation produced no braille Unicode output');
                    }
                    self.postMessage({ id, type: 'translate', result: { success: true, translation: result } });
                } catch (e) {
                    var logTail = '';
                    try {
                        var tail = recentLogs.slice(-8).join('\n');
                        if (tail) {
                            logTail = '\nRecent liblouis logs:\n' + tail;
                        }
                    } catch (_) {}
                    const message = 'Translation failed for table ' + selectedTable + ': ' + (e && e.message ? e.message : 'Unknown error') + logTail;
                    throw new Error(message);
                }
                break;

            case 'backTranslate': {
                if (!liblouisReady || !liblouisInstance) {
                    throw new Error('Liblouis not initialized');
                }

                const braille = data.braille;
                const backTable = data.tableName || DEFAULT_TABLE;

                // unicode.dis is what makes liblouis read the U+2800 block as
                // braille cells rather than as literal characters, so the same
                // chain used for translation is used in reverse.
                const backChain = backTable.indexOf('unicode.dis') !== -1
                    ? backTable
                    : ('unicode.dis,' + backTable);

                console.log('Worker: Back-translating braille with table:', backChain);

                try {
                    const text = liblouisInstance.backTranslateString(backChain, braille);
                    if (typeof text !== 'string') {
                        throw new Error('Liblouis returned no text');
                    }
                    self.postMessage({ id, type: 'backTranslate', result: { success: true, text: text } });
                } catch (e) {
                    var backLogTail = '';
                    try {
                        var backTail = recentLogs.slice(-8).join('\n');
                        if (backTail) {
                            backLogTail = '\nRecent liblouis logs:\n' + backTail;
                        }
                    } catch (_) {}
                    throw new Error('Back-translation failed for table ' + backTable + ': ' +
                        (e && e.message ? e.message : 'Unknown error') + backLogTail);
                }
                break;
            }

            default:
                throw new Error('Unknown message type: ' + type);
        }
    } catch (error) {
        console.error('Worker: Error handling message:', error);
        self.postMessage({ id, type: e.data.type, result: { success: false, error: error.message } });
    }
};

console.log('Worker: Liblouis worker script loaded');
