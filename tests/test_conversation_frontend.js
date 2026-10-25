const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const app = fs.readFileSync('public/app.js', 'utf8');

function extractFunction(source, signature) {
    const start = source.indexOf(signature);
    assert.notEqual(start, -1, `found ${signature}`);
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
    assert.notEqual(end, -1, `complete ${signature}`);
    return source.slice(start, end);
}

const transcriptFn = new Function(`${extractFunction(app, '    function formatConversationText(conv) {')}; return formatConversationText;`)();
const transcript = transcriptFn({
    title: 'Semester notes',
    messages: [
        { sender: 'user', text: 'Show a code sample' },
        { sender: 'assistant', text: 'Full answer:\n```python\nprint("complete")\n```\nAnd the explanation.' },
        { sender: 'system', text: 'must not export' }
    ]
});
assert.match(transcript, /^Semester notes\n\nYou:\nShow a code sample/m);
assert.ok(transcript.includes('Full answer:\n```python\nprint("complete")\n```\nAnd the explanation.'));
assert.ok(!transcript.includes('must not export'));
assert.match(extractFunction(app, '    function exportConversation(conv) {'), /text\/plain;charset=utf-8/);
assert.match(extractFunction(app, '    function exportConversation(conv) {'), /_export\.txt/);

class FakeNode {
    constructor() {
        this.children = [];
        this.listeners = {};
        this.attributes = {};
        this.dataset = {};
        this.classList = { add() {}, remove() {} };
        this.label = { textContent: 'Copy' };
    }
    appendChild(child) { this.children.push(child); }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(type, handler) { this.listeners[type] = handler; }
    querySelector() { return this.label; }
}

async function testCopyControl() {
    const copied = [];
    const alerts = [];
    const document = { createElement: () => new FakeNode() };
    const navigator = { clipboard: { writeText: async text => copied.push(text) } };
    const copyFn = new Function('document', 'navigator', 'showGlobalAlert', 'setTimeout',
        `${extractFunction(app, '    function appendAssistantCopyControl(wrapper, responseText) {')}; return appendAssistantCopyControl;`)(
        document, navigator, (...args) => alerts.push(args), () => 0
    );
    const wrapper = new FakeNode();
    copyFn(wrapper, 'Complete answer\n```js\nconst x = 1;\n```');
    const button = wrapper.children[0].children[0];
    assert.equal(button.attributes['aria-label'], 'Copy response');
    await button.listeners.click({ stopPropagation() {} });
    assert.deepEqual(copied, ['Complete answer\n```js\nconst x = 1;\n```']);
    assert.equal(alerts[0][0], 'Response copied to clipboard.');

    navigator.clipboard.writeText = async () => { throw new Error('clipboard unavailable'); };
    await button.listeners.click({ stopPropagation() {} });
    assert.equal(alerts[1][1], 'warning');
}

async function run() {
    await testCopyControl();
    for (const signature of [
        '    function appendAssistantFallbackMessage(queryText, messageText) {',
        '    function appendGeneralKnowledgeMessage(answerText, correspondingQuestion = null) {',
        '    function appendAssistantNoAnswerMessage(queryText, messageText) {',
        '    function appendAssistantErrorMessage(errorText, correspondingQuestion = null) {'
    ]) assert.match(extractFunction(app, signature), /appendAssistantCopyControl\(wrapper,/);
    assert.match(extractFunction(app, '    function appendAssistantMessage('), /btn-copy-response/);
    assert.match(extractFunction(app, '    async function shareConversation(conv) {'), /\/api\/conversations\/\$\{encodeURIComponent\(conv\.id\)\}\/share/);

    const viewer = fs.readFileSync('public/share.js', 'utf8');
    assert.match(viewer, /credentials: 'omit'/);
    assert.match(viewer, /text\.textContent = message\.text/);
    assert.doesNotMatch(viewer, /innerHTML/);

    class ViewerNode {
        constructor(tagName = '') { this.tagName = tagName; this.children = []; this.attributes = {}; this.textContent = ''; }
        replaceChildren(...children) { this.children = children; }
        appendChild(child) { this.children.push(child); }
        append(...children) { this.children.push(...children); }
        setAttribute(name, value) { this.attributes[name] = value; }
    }
    const host = new ViewerNode('section');
    const titleText = 'Shared <script>title</script>';
    const assistantText = 'Complete answer\n```python\nprint(42)\n```';
    let fetchCall;
    const context = {
        document: { getElementById: () => host, createElement: tag => new ViewerNode(tag), title: '' },
        window: { location: { pathname: '/share/' + 'a'.repeat(43) } },
        fetch: async (...args) => {
            fetchCall = args;
            return { ok: true, json: async () => ({ title: titleText, messages: [
                { sender: 'user', text: 'Question' }, { sender: 'assistant', text: assistantText }
            ] }) };
        },
        encodeURIComponent
    };
    vm.runInNewContext(viewer, context);
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(fetchCall[0], `/shared/${'a'.repeat(43)}`);
    assert.equal(fetchCall[1].credentials, 'omit');
    assert.equal(fetchCall[1].cache, 'no-store');
    assert.equal(host.children[0].textContent, titleText);
    assert.equal(host.children[2].children[1].textContent, assistantText);
    assert.equal(host.attributes['aria-busy'], 'false');
}

run().then(() => console.log('Conversation frontend tests passed.')).catch(error => {
    process.stderr.write(`${error.stack}\n`);
    process.exitCode = 1;
});
