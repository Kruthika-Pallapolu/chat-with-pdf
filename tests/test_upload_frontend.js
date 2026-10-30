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
assert.match(source, /setPdfUploadStatus\(\s*'uploading',\s*'Uploading your PDF\.\.\.',\s*'Your document is being uploaded securely\.'\s*\)/,
    'the upload state shows the secure upload title and message');
assert.match(source, /if \(!uploadSettled && status\.stage === 'processing'\)/,
    'the processing copy appears only when the backend reports processing');
assert.doesNotMatch(source, /status\.stage === 'uploading'\)\s*\{\s*setPdfUploadStatus\('processing'/,
    'uploading status is not mislabeled as processing');
assert.match(source, /setPdfUploadStatus\(\s*'processing',\s*'Processing your PDF\.\.\.',\s*"We're extracting the text and preparing your document for AI-powered search\. This may take a minute or two, depending on the PDF's size\. Please keep this page open while processing completes\."\s*\)/,
    'processing copy explains the work and asks users to keep the page open');
assert.match(source, /setPdfUploadStatus\('ready', 'Your PDF is ready! You can now ask questions about it\.'\)/,
    'success appears only after the upload API confirms success');
assert.match(source, /method: 'POST',\s*body: formData/,
    'the upload continues to use the existing multipart POST request');
assert.match(source, /if \(pdfUploadInProgress\) \{\s*showGlobalAlert\('A PDF upload is already being processed\.'/,
    'duplicate uploads remain blocked while an upload is in progress');
assert.match(source, /!uploadSettled && status\.stage === 'processing'/,
    'polling cannot replace success or error state after the upload request settles');
const html = fs.readFileSync('public/index.html', 'utf8');
assert.match(html, /id="pdfUploadStatus"[^>]*role="status"[^>]*aria-live="polite"/,
    'upload status remains available to assistive technology');
assert.match(html, /id="pdfUploadStatusDetail"[^>]*hidden/,
    'supporting status copy has a dedicated hidden-until-needed element');
const uploadCss = fs.readFileSync('public/style.css', 'utf8');
assert.match(uploadCss, /\.pdf-upload-status\s*\{[^}]*overflow-wrap:\s*anywhere;[^}]*min-width:\s*0;/s,
    'status copy wraps within narrow desktop and mobile containers');
assert.match(uploadCss, /\.pdf-upload-status-content\s*\{[^}]*min-width:\s*0;/s,
    'status text can shrink and wrap inside the flex row');
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
