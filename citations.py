"""
Citation helpers (pure Python, no heavy dependencies).

Goal: turn "the model says it used sources S1,S3" into citations the frontend can
trust, WITHOUT treating a high retrieval score as proof of support.

Contract
--------
* The model is asked to end its answer with a line:  SOURCES: S1,S3
  (S<n> = the n-th retrieved chunk, in the order given to build_context()).
* parse_sources_line() validates every id against the number of chunks that were
  actually supplied. Unknown / out-of-range / duplicate ids are dropped.
* find_evidence() only returns a passage when the cited chunk really contains a
  window of text that the answer reproduces (lexical support test, thresholds
  below). Otherwise there is no evidence and the frontend must navigate to the
  page WITHOUT highlighting.
* Nothing here falls back to "top retrieval score".
"""

import re
import unicodedata

# ---- tunable thresholds -------------------------------------------------
MIN_MATCHED_TOKENS = 4        # distinct content tokens of the window found in the answer
MIN_CONTAINMENT = 0.70        # share of the window's content tokens found in the answer
MIN_SHARED_RUN = 3            # consecutive words that appear verbatim in both texts
MAX_UNIT_CHARS = 220          # longer sentences are split into word windows
UNIT_WORDS = 30
MAX_EVIDENCE_CHARS = 400
MAX_WINDOW_UNITS = 2

_STOP = {
    "the", "and", "for", "that", "with", "this", "from", "are", "was", "were",
    "has", "have", "had", "not", "but", "can", "will", "all", "any", "its",
    "their", "they", "them", "which", "who", "what", "when", "where", "into",
    "such", "than", "then", "also", "each", "one", "may", "must", "shall",
    "should", "would", "could", "been", "being", "about", "over", "under",
}

_LABEL_RE = re.compile(r"^[\W_]*sources?\s*[*_]*\s*:", re.IGNORECASE)


def _norm(text):
    return unicodedata.normalize("NFKC", text or "").lower()


def _words(text):
    return re.findall(r"[^\W_]+", _norm(text), flags=re.UNICODE)


def _content_tokens(text):
    return [w for w in _words(text) if len(w) >= 3 and w not in _STOP]


# ---- source id validation ----------------------------------------------

def parse_sources_line(answer, n_sources):
    """
    Remove a trailing 'SOURCES: S1,S3' line and return (clean_answer, ids, rejected).

    ids      -> 0-based chunk indexes, validated against n_sources, de-duplicated,
                order preserved.
    rejected -> ids the model produced that do not exist (reported, never used).
    The line is only recognised as the LAST non-empty line, so a sentence in the
    body that merely starts with the word "Sources" is never stripped.
    """
    if not answer:
        return answer, [], []
    lines = answer.rstrip().split("\n")
    last = lines[-1]
    if not _LABEL_RE.match(last):
        return answer.strip(), [], []

    clean = "\n".join(lines[:-1]).rstrip()
    ids, rejected = [], []
    for m in re.finditer(r"\bS\s*(\d+)\b", last, flags=re.IGNORECASE):
        k = int(m.group(1))
        if 1 <= k <= n_sources:
            if k - 1 not in ids:
                ids.append(k - 1)
        else:
            rejected.append(f"S{k}")
    return clean, ids, rejected


# ---- evidence ------------------------------------------------------------

def _units(normalized):
    """Split whitespace-normalised text into (start, end) units (sentences, or word windows)."""
    spans = []
    pos = 0
    for part in re.split(r"(?<=[.!?])\s+", normalized):
        start = normalized.find(part, pos)
        if start < 0:
            continue
        end = start + len(part)
        pos = end
        if not part.strip():
            continue
        if len(part) <= MAX_UNIT_CHARS:
            spans.append((start, end))
            continue
        words = list(re.finditer(r"\S+", part))
        for i in range(0, len(words), UNIT_WORDS):
            grp = words[i:i + UNIT_WORDS]
            spans.append((start + grp[0].start(), start + grp[-1].end()))
    return spans


def _has_shared_run(window_text, answer_words_joined):
    ww = _words(window_text)
    if len(ww) < MIN_SHARED_RUN:
        return False
    for i in range(len(ww) - MIN_SHARED_RUN + 1):
        gram = " ".join(ww[i:i + MIN_SHARED_RUN])
        if (" " + gram + " ") in answer_words_joined:
            return True
    return False


def find_evidence(answer, chunk_text):
    """
    Return {"text", "start_ratio", "matched", "containment"} for the window of
    chunk_text that the answer demonstrably reproduces, or None.
    """
    if not answer or not chunk_text:
        return None
    normalized = re.sub(r"\s+", " ", chunk_text).strip()
    if not normalized:
        return None

    answer_set = set(_content_tokens(answer))
    answer_joined = " " + " ".join(_words(answer)) + " "
    units = _units(normalized)

    best = None  # (matched, -length, containment, start, end)
    for i in range(len(units)):
        for w in range(1, MAX_WINDOW_UNITS + 1):
            if i + w > len(units):
                break
            start, end = units[i][0], units[i + w - 1][1]
            if end - start > MAX_EVIDENCE_CHARS:
                break
            text = normalized[start:end]
            toks = set(_content_tokens(text))
            if not toks:
                continue
            matched = len(toks & answer_set)
            containment = matched / len(toks)
            if matched < MIN_MATCHED_TOKENS or containment < MIN_CONTAINMENT:
                continue
            if not _has_shared_run(text, answer_joined):
                continue
            cand = (matched, -(end - start), containment, start, end)
            if best is None or cand[:2] > best[:2]:
                best = cand
    if best is None:
        return None
    matched, _neg, containment, start, end = best
    return {
        "text": normalized[start:end],
        "start_ratio": start / max(1, len(normalized)),
        "matched": matched,
        "containment": round(containment, 3),
    }


# ---- assembling the response field --------------------------------------

def build_citations(answer, results, cited_indexes, page_texts=None):
    """
    One entry per supplied chunk selected by the answer support check.

    evidence is None unless the support test passed -> frontend: page only.
    position_hint (0..1, approximate) is only used by the frontend to choose
    between several identical matches on the page; it is None when the chunk
    text is not found exactly once in the page text.
    """
    out = []
    for idx in cited_indexes:
        if not (0 <= idx < len(results)):
            continue
        r = results[idx]
        page = r.get("page")
        ev = find_evidence(answer, r.get("text", ""))
        hint = None
        if ev and page_texts and isinstance(page, int) and 1 <= page <= len(page_texts):
            pt = page_texts[page - 1] or ""
            ct = r.get("text", "")
            if ct and pt.count(ct) == 1:
                pos = pt.find(ct) + ev["start_ratio"] * len(ct)
                hint = round(pos / max(1, len(pt)), 4)
        out.append({
            "source_id": f"S{idx + 1}",
            "page": page,
            "evidence": ev["text"] if ev else None,
            "evidence_verified": bool(ev),
            "position_hint": hint,
        })
    return out


def filter_supported_answer(answer, results):
    """Keep answer sentences with lexical support in at least one supplied chunk.

    Returns the supported text, supporting chunk indexes, and whether any text
    was omitted. This deliberately reuses the same conservative evidence check
    used for citation highlighting.
    """
    if not answer:
        return "", [], False

    units = re.split(r"(?<=[.!?])\s+|\n(?=\s*(?:[-*•]|\d+[.)]))", answer.strip())
    supported, indexes = [], set()
    omitted = False
    for unit in units:
        unit = unit.strip()
        if not unit:
            continue
        plain_unit = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", unit).strip()
        answer_tokens = set(_content_tokens(plain_unit))
        matched_indexes = []
        for index, result in enumerate(results):
            source_text = result.get("text", "")
            source_tokens = set(_content_tokens(source_text))
            if (
                answer_tokens
                and len(answer_tokens & source_tokens) / len(answer_tokens) >= MIN_CONTAINMENT
                and find_evidence(plain_unit, source_text)
            ):
                matched_indexes.append(index)
        if matched_indexes:
            supported.append(unit)
            indexes.update(matched_indexes)
        else:
            omitted = True

    return "\n".join(supported), sorted(indexes), omitted
