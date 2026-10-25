/*
 * CWP citation highlight matcher (pure functions, no DOM).
 *
 * locate(items, evidenceText, hint) maps a verified evidence passage onto PDF.js
 * text items. It matches on a "compact" form (letters+digits only, NFKC, lower-case)
 * so PDF.js item boundaries, whitespace-only items, ligatures, soft/line-end hyphens
 * and punctuation cannot break the match, and it keeps a char -> (item, offset) map.
 *
 * It NEVER guesses: not found, too short, or ambiguous => { ok:false, reason }.
 * The caller then shows the page without any highlight.
 */
(function (root) {
  'use strict';

  var MIN_COMPACT_CHARS = 20; // evidence shorter than this is too weak to locate safely
  var AMBIGUITY_GAP = 0.1;    // required hint-distance margin between best and 2nd-best match
  var LETTER_OR_DIGIT = /[\p{L}\p{N}]/u;

  function compactString(str) {
    var out = '';
    var s = String(str || '');
    for (var i = 0; i < s.length; i++) {
      var n = s[i].normalize('NFKC').toLowerCase();
      for (var j = 0; j < n.length; j++) if (LETTER_OR_DIGIT.test(n[j])) out += n[j];
    }
    return out;
  }

  // Returns { text, map } where map[k] = [itemIndex, offsetInItem] for compact char k.
  function buildPageIndex(items) {
    var chars = [];
    var map = [];
    for (var k = 0; k < items.length; k++) {
      var s = (items[k] && items[k].str) || '';
      for (var i = 0; i < s.length; i++) {
        var n = s[i].normalize('NFKC').toLowerCase();
        for (var j = 0; j < n.length; j++) {
          if (LETTER_OR_DIGIT.test(n[j])) { chars.push(n[j]); map.push([k, i]); }
        }
      }
    }
    return { text: chars.join(''), map: map };
  }

  function findAll(hay, needle) {
    var res = [];
    var p = hay.indexOf(needle);
    while (p !== -1) { res.push(p); p = hay.indexOf(needle, p + 1); }
    return res;
  }

  function locate(items, evidenceText, hint) {
    var ev = compactString(evidenceText);
    if (ev.length < MIN_COMPACT_CHARS) return { ok: false, reason: 'evidence-too-short' };
    var idx = buildPageIndex(items || []);
    var hits = findAll(idx.text, ev);
    if (hits.length === 0) return { ok: false, reason: 'not-found' };

    var start = hits[0];
    if (hits.length > 1) {
      if (typeof hint !== 'number' || !isFinite(hint)) return { ok: false, reason: 'ambiguous' };
      var total = Math.max(1, idx.text.length);
      var ranked = hits
        .map(function (h) { return { h: h, d: Math.abs(h / total - hint) }; })
        .sort(function (a, b) { return a.d - b.d; });
      if (ranked[1].d - ranked[0].d < AMBIGUITY_GAP) return { ok: false, reason: 'ambiguous' };
      start = ranked[0].h;
    }

    var segments = [];
    for (var c = start; c < start + ev.length; c++) {
      var m = idx.map[c];
      var last = segments[segments.length - 1];
      if (last && last.itemIndex === m[0]) {
        last.end = m[1] + 1;
      } else {
        segments.push({ itemIndex: m[0], start: m[1], end: m[1] + 1 });
      }
    }
    return { ok: true, segments: segments, matches: hits.length };
  }

  var api = { locate: locate, compactString: compactString, buildPageIndex: buildPageIndex };
  root.CWPHighlight = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
