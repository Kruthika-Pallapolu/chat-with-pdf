const assert = require('node:assert/strict');
const fs = require('node:fs');

const source = fs.readFileSync('public/app.js', 'utf8');
const start = source.indexOf('    async function readJsonResponseSafely(response) {');
assert.notEqual(start, -1, 'safe JSON response helper exists');

let depth = 0;
let end = -1;
for (let index = source.indexOf('{', start); index < source.length; index += 1) {
    if (source[index] === '{') depth += 1;
    if (source[index] === '}') depth -= 1;
    if (depth === 0) {
        end = index + 1;
        break;
    }
}
assert.notEqual(end, -1, 'safe JSON response helper is complete');
const readJsonResponseSafely = new Function(`${source.slice(start, end)}; return readJsonResponseSafely;`)();
const successPathStart = source.indexOf('if (res.ok && data.success) {', source.indexOf('async function handlePdfFileUpload'));
const documentUpdate = source.indexOf('updateDocumentUI(data.document);', successPathStart);
const freshConversation = source.indexOf('createNewConversation();', successPathStart);
assert.ok(documentUpdate < freshConversation, 'new conversation saves with the new document hash');
assert.match(source, /if \(pdfUploadInProgress\) \{\s*conversationSavePending = true;/,
    'conversation writes are deferred during a replacement upload');
assert.match(source, /Upload completion could not be confirmed\./,
    'ambiguous network failures do not claim the PDF was rejected');

async function run() {
    let parsed = false;
    const html502 = await readJsonResponseSafely({
        headers: { get: () => 'text/html; charset=utf-8' },
        json: async () => { parsed = true; throw new SyntaxError('HTML is not JSON'); }
    });
    assert.equal(html502, null);
    assert.equal(parsed, false, 'HTML gateway responses are not parsed as JSON');

    const empty502 = await readJsonResponseSafely({
        headers: { get: () => 'application/json' },
        json: async () => { throw new SyntaxError('empty body'); }
    });
    assert.equal(empty502, null);

    const valid = await readJsonResponseSafely({
        headers: { get: () => 'application/json' },
        json: async () => ({ detail: 'unavailable' })
    });
    assert.deepEqual(valid, { detail: 'unavailable' });
}

run().catch(error => {
    process.stderr.write(`${error.stack}\n`);
    process.exitCode = 1;
});
