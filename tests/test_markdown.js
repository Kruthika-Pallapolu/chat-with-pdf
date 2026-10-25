const assert = require('assert');
const { render } = require('../public/markdown.js');

const unordered = render('* First point\n* Second point\n- Third point');
assert.match(unordered, /<ul><li>First point<\/li><li>Second point<\/li><li>Third point<\/li><\/ul>/);
assert.strictEqual((unordered.match(/<li>/g) || []).length, 3);

const formatted = render('# Heading\n\n**Bold** and *italic* with `inline code`.\n\n1. Number one\n2. Number two\n\nNext paragraph.');
assert.match(formatted, /<h1>Heading<\/h1>/);
assert.match(formatted, /<strong>Bold<\/strong>/);
assert.match(formatted, /<em>italic<\/em>/);
assert.match(formatted, /<code>inline code<\/code>/);
assert.match(formatted, /<ol><li>Number one<\/li><li>Number two<\/li><\/ol>/);
assert.match(formatted, /<p>Next paragraph\.<\/p>/);

const fenced = render('```html\n<script>alert(1)</script>\n```');
assert.match(fenced, /<pre><code>&lt;script&gt;alert\(1\)&lt;\/script&gt;<\/code><\/pre>/);
assert.doesNotMatch(fenced, /<script>/);

const citation = render('Supported statement [S1].');
assert.match(citation, /\[S1\]/);

console.log('Markdown rendering tests passed.');