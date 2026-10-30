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
const classifierStart = source.indexOf('    function classifyPdfUploadFailure(error, uploadRequestStarted) {');
assert.notEqual(classifierStart, -1, 'upload failure classifier exists');
let classifierDepth = 0;
let classifierEnd = -1;
for (let index = source.indexOf('{', classifierStart); index < source.length; index += 1) {
    if (source[index] === '{') classifierDepth += 1;
    if (source[index] === '}') classifierDepth -= 1;
    if (classifierDepth === 0) {
        classifierEnd = index + 1;
        break;
    }
}
assert.notEqual(classifierEnd, -1, 'upload failure classifier is complete');
const classifyPdfUploadFailure = new Function(
    `${source.slice(classifierStart, classifierEnd)}; return classifyPdfUploadFailure;`
)();
assert.equal(classifyPdfUploadFailure({ name: 'AbortError' }, true), 'aborted_request');
assert.equal(classifyPdfUploadFailure({ name: 'TypeError' }, true), 'network_rejection');
assert.equal(classifyPdfUploadFailure(new Error('preparation failed'), false), 'client_preflight_failure');
assert.match(source, /logPdfUploadOutcome\('server_success'/, 'backend-confirmed success is logged');
assert.match(source, /logPdfUploadOutcome\(res\.ok \? 'server_rejection' : 'http_error'/,
    'HTTP and application rejection responses are logged separately');
assert.match(source, /console\.warn\(`\[pdf-upload\] \$\{details\}`\)/,
    'client diagnostics omit exception text and upload contents');
const successPathStart = source.indexOf('if (res.ok && data.success) {', source.indexOf('async function handlePdfFileUpload'));
const documentUpdate = source.indexOf('updateDocumentUI(data.document);', successPathStart);
const freshConversation = source.indexOf('createNewConversation();', successPathStart);
assert.ok(documentUpdate < freshConversation, 'new conversation saves with the new document hash');
assert.match(source, /setPdfUploadStatus\('ready', 'PDF loaded successfully!'\)/,
    'successful processing shows the requested confirmation');
assert.match(source, /!uploadSettled && \(status\.stage === 'uploading' \|\| status\.stage === 'processing'\)/,
    'polling cannot replace the success state after the upload request settles');
const uploadCss = fs.readFileSync('public/style.css', 'utf8');
assert.match(uploadCss, /\.pdf-upload-status\[data-state="ready"\] \.pdf-upload-spinner\s*\{\s*display: none;/,
    'the spinner is hidden only for the backend-confirmed ready state');
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
