const assert = require('node:assert/strict');
const fs = require('node:fs');

const source = fs.readFileSync('public/app.js', 'utf8');
const html = fs.readFileSync('public/index.html', 'utf8');
const css = fs.readFileSync('public/style.css', 'utf8');

function extractFunction(name) {
    const start = source.indexOf(`function ${name}(`);
    assert.notEqual(start, -1, `${name} exists`);
    const openBrace = source.indexOf('{', start);
    let depth = 0;
    for (let index = openBrace; index < source.length; index += 1) {
        if (source[index] === '{') depth += 1;
        if (source[index] === '}') depth -= 1;
        if (depth === 0) return source.slice(start, index + 1);
    }
    assert.fail(`${name} is complete`);
}

const getDefaultWorkspaceViewMode = new Function(
    `${extractFunction('getDefaultWorkspaceViewMode')}; return getDefaultWorkspaceViewMode;`
)();
const bindViewModeControls = extractFunction('bindViewModeControls');

function makeWorkspace(initiallyMobile) {
    let selectedMode = null;
    let mediaChangeHandler = null;
    const buttons = ['pdf', 'split', 'chat'].map(mode => ({
        mode,
        handler: null,
        getAttribute(name) {
            return name === 'data-mode' ? this.mode : null;
        },
        addEventListener(name, handler) {
            if (name === 'click') this.handler = handler;
        },
        click() {
            this.handler();
        },
    }));
    const mediaQuery = {
        matches: initiallyMobile,
        addEventListener(name, handler) {
            if (name === 'change') mediaChangeHandler = handler;
        },
    };
    const windowMock = { matchMedia: () => mediaQuery };
    const harness = new Function(
        'viewModeToggleBtns',
        'window',
        'setWorkspaceViewMode',
        'getDefaultWorkspaceViewMode',
        `${bindViewModeControls};
         let hasManuallySelectedWorkspaceView = false;
         bindViewModeControls();
         return {
             manuallySelected: () => hasManuallySelectedWorkspaceView,
         };`
    )(
        buttons,
        windowMock,
        mode => { selectedMode = mode; },
        getDefaultWorkspaceViewMode,
    );

    return {
        buttons,
        currentMode: () => selectedMode,
        manuallySelected: harness.manuallySelected,
        resize: matches => {
            mediaQuery.matches = matches;
            mediaChangeHandler({ matches });
        },
    };
}

assert.equal(getDefaultWorkspaceViewMode(false), 'split', 'desktop defaults to the existing split view');
assert.equal(getDefaultWorkspaceViewMode(true), 'chat', 'mobile defaults to chat-only view');
assert.match(html, /id="workspaceContainer" class="workspace-container mode-split"/,
    'desktop keeps the existing split workspace markup');
assert.match(css, /\.workspace-container\.mode-split #pdfPanel\s*\{[^}]*width:\s*50%;/s,
    'desktop split view keeps the PDF at half width');
assert.match(css, /\.workspace-container\.mode-split #chatPanel\s*\{[^}]*width:\s*50%;/s,
    'desktop split view keeps chat at half width');
assert.match(css, /\.workspace-container\.mode-chat #pdfPanel\s*\{\s*display:\s*none;/,
    'chat mode hides the PDF panel');
assert.match(css, /\.workspace-container\.mode-chat #chatPanel\s*\{[^}]*width:\s*100%;/s,
    'chat mode fills the workspace width');

const desktop = makeWorkspace(false);
assert.equal(desktop.currentMode(), 'split', 'desktop initializes split mode');
desktop.resize(true);
assert.equal(desktop.currentMode(), 'chat', 'an unmodified desktop default adapts to mobile');
desktop.resize(false);
assert.equal(desktop.currentMode(), 'split', 'an unmodified mobile default adapts back to desktop');

const mobile = makeWorkspace(true);
assert.equal(mobile.currentMode(), 'chat', 'mobile initializes chat-only mode');
mobile.buttons.find(button => button.mode === 'pdf').click();
assert.equal(mobile.currentMode(), 'pdf', 'mobile can switch to PDF-only view');
mobile.buttons.find(button => button.mode === 'chat').click();
assert.equal(mobile.currentMode(), 'chat', 'mobile can switch back to chat-only view');
assert.equal(mobile.manuallySelected(), true, 'view button clicks mark the selection as manual');
mobile.resize(false);
assert.equal(mobile.currentMode(), 'chat', 'resizing does not override a manually selected view');

console.log('Workspace view-mode tests passed.');
