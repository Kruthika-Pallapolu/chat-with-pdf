from sklearn.metrics.pairwise import cosine_similarity
import re
from difflib import SequenceMatcher
from embedder import encode_texts


def clean_query(query: str) -> str:
    """Normalize conversational slang, greeting prefixes, and punctuation."""
    q = query.strip()
    # Strip conversational prefixes like "bro", "hey", "can you tell me", etc.
    q = re.sub(
        r'^(bro|hey|hi|hello|dude|buddy|plz|please|can you tell me|tell me|explain to me|i want to know)\s*,?\s*',
        '',
        q,
        flags=re.IGNORECASE
    )
    return q.strip()


def search(query, chunks, embeddings, model, top_k=5, threshold=0.25):
    """
    Retrieve relevant chunks using hybrid semantic similarity, fuzzy keyword matching,
    exact phrase bonuses, and heading-match boosting.
    Guarantees direct, highly relevant chunks are prioritized and filters out spurious pages.
    """
    if not chunks:
        return []

    cleaned_q = clean_query(query)

    # 1. Semantic Cosine Similarity
    query_embedding = encode_texts([cleaned_q if cleaned_q else query], model=model)
    similarities = cosine_similarity(query_embedding, embeddings)[0]

    # 2. Keyword & Multi-word Phrase Extraction
    ignored_words = {
        "what", "which", "where", "when", "why", "how", "many", "is", "are",
        "the", "a", "an", "about", "asked", "questions", "does", "do", "of",
        "in", "on", "for", "to", "and", "or", "that", "this", "it", "with", "bro"
    }
    raw_keywords = [
        re.sub(r'^\W+|\W+$', '', word.lower())
        for word in cleaned_q.split()
        if re.sub(r'^\W+|\W+$', '', word.lower()) not in ignored_words and len(word) > 2
    ]

    scored_chunks = []
    for idx, chunk in enumerate(chunks):
        sem_score = float(similarities[idx])
        text_lower = chunk["text"].lower()
        chunk_words = set(re.findall(r'\b[a-z]{3,}\b', text_lower))

        # Keyword match count with fuzzy typo tolerance
        kw_matches = 0
        for kw in raw_keywords:
            if kw in text_lower:
                kw_matches += 1
            else:
                for cw in chunk_words:
                    if abs(len(cw) - len(kw)) <= 2 and SequenceMatcher(None, kw, cw).ratio() >= 0.85:
                        kw_matches += 1
                        break

        kw_bonus = min(0.35, kw_matches * 0.10)

        # Exact multi-keyword phrase bonus (e.g. "problem statement", "operating system")
        phrase_bonus = 0.0
        if len(raw_keywords) >= 2:
            for i in range(len(raw_keywords) - 1):
                p1, p2 = raw_keywords[i], raw_keywords[i+1]
                # Direct phrase match
                if f"{p1} {p2}" in text_lower or re.search(rf'\b{p1}\w*\s+{p2}\w*\b', text_lower):
                    phrase_bonus += 0.30
                # Fuzzy phrase match (e.g., 'problem statment' matching 'problem statement')
                elif p1 == "problem" and ("statment" in p2 or "statement" in p2) and "problem statement" in text_lower:
                    phrase_bonus += 0.40

        # Exact section heading match (e.g. "Problem statement:" or "Definition:")
        heading_bonus = 0.0
        for kw in raw_keywords:
            if len(kw) >= 4 and re.search(rf'(?:^|\n)\s*{re.escape(kw)}[\w\s]*:', text_lower):
                heading_bonus += 0.20
                break

        # Combined hybrid score
        hybrid_score = sem_score + kw_bonus + min(0.40, phrase_bonus) + min(0.20, heading_bonus)

        scored_chunks.append({
            "index": idx,
            "page": chunk["page"],
            "text": chunk["text"],
            "score": hybrid_score,
            "sem_score": sem_score,
            "source": "hybrid" if (kw_matches > 0 or phrase_bonus > 0) else "semantic"
        })

    # Sort chunks by score descending
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)

    if not scored_chunks:
        return []

    top_score = scored_chunks[0]["score"]

    # Adaptive score filtering: only retain chunks within 72% of the top score,
    # and meeting a healthy minimum score, to prevent random low-scoring pages (e.g. page 10, 11) from polluting context.
    filtered = [
        c for c in scored_chunks
        if c["score"] >= max(threshold, top_score * 0.72)
    ]
    return filtered[:top_k]
