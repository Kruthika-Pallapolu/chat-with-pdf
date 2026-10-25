(function (root) {
  'use strict';

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function renderInline(text) {
    return String(text).split(/(`[^`\n]+`)/g).map(part => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return `<code>${escapeHtml(part.slice(1, -1))}</code>`;
      }

      return escapeHtml(part)
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')
        .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')
        .replace(/(^|[^_])_([^_\n]+)_(?!_)/g, '$1<em>$2</em>');
    }).join('');
  }

  function render(markdown) {
    if (!markdown) return '';

    const lines = String(markdown).replace(/\r\n?/g, '\n').split('\n');
    const output = [];
    let paragraph = [];
    let listTag = null;
    let listItems = [];
    let codeLines = null;

    function flushParagraph() {
      if (!paragraph.length) return;
      output.push(`<p>${paragraph.map(renderInline).join('<br>')}</p>`);
      paragraph = [];
    }

    function closeList() {
      if (!listTag) return;
      output.push(`<${listTag}>${listItems.map(item => `<li>${renderInline(item)}</li>`).join('')}</${listTag}>`);
      listTag = null;
      listItems = [];
    }

    function flushCode() {
      output.push(`<pre><code>${codeLines.map(escapeHtml).join('\n')}</code></pre>`);
      codeLines = null;
    }

    for (const line of lines) {
      if (/^\s*```/.test(line)) {
        flushParagraph();
        closeList();
        if (codeLines === null) codeLines = [];
        else flushCode();
        continue;
      }

      if (codeLines !== null) {
        codeLines.push(line);
        continue;
      }

      if (!line.trim()) {
        flushParagraph();
        closeList();
        continue;
      }

      const heading = line.match(/^ {0,3}(#{1,6})[ \t]+(.+?)\s*#*\s*$/);
      if (heading) {
        flushParagraph();
        closeList();
        const level = heading[1].length;
        output.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        continue;
      }

      const unorderedItem = line.match(/^ {0,3}[-+*][ \t]+(.+?)\s*$/);
      const orderedItem = line.match(/^ {0,3}\d+[.)][ \t]+(.+?)\s*$/);
      const item = unorderedItem || orderedItem;
      if (item) {
        flushParagraph();
        const nextTag = unorderedItem ? 'ul' : 'ol';
        if (listTag && listTag !== nextTag) closeList();
        listTag = nextTag;
        listItems.push(item[1]);
        continue;
      }

      closeList();
      paragraph.push(line);
    }

    flushParagraph();
    closeList();
    if (codeLines !== null) flushCode();
    return output.join('\n');
  }

  const api = { render };
  root.CWPMarkdown = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);