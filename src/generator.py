import os
import time
import logging
from datetime import datetime, timezone

from google import genai
from google.genai import types
from google.genai.errors import ServerError
from sentence_transformers import SentenceTransformer

from search import search
from pdf_loader import extract_text
from chunker import chunk_text
from storage import get_file_hash
from document_search import find_module_headings


# Gemini models
PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-3.8-flash"
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))


# Load the embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")
logger = logging.getLogger("cwp.generator")


def get_client():
    """
    Returns a Gemini Client using GEMINI_API_KEY or GOOGLE_API_KEY from environment.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key and api_key not in ["dummy_key_for_load", "AIzaSy_placeholder_key_for_load"]:
        return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS))
    return genai.Client(
        api_key="AIzaSy_placeholder_key_for_load",
        http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
    )


# Module-level client instance for backward compatibility
client = get_client()


def create_embeddings(chunks):
    """
    Create an embedding vector for every chunk.
    """
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts)
    return embeddings


def is_broad_query(query: str) -> bool:
    """
    Check whether the question is a broad summary, key concepts, or document-wide inquiry.
    """
    q = query.lower()
    keywords = [
        "key concept", "key topics", "main concept", "main topic",
        "summarize", "summary", "overview", "what is this document about",
        "about this document", "about this pdf", "main points", "core topics",
        "topics discussed", "covered in this document", "covered in this pdf",
        "document summary", "what does this document cover", "what is covered",
        "what are the key concepts"
    ]
    return any(k in q for k in keywords)


def retrieve(query, chunks, embeddings, top_k=5):
    """
    Retrieve the most relevant chunks for the user's question.
    For broad/summary questions, samples chunks across the document.
    """
    if is_broad_query(query) and len(chunks) > top_k:
        total = len(chunks)
        sample_count = min(18, total)
        step = max(1, total // sample_count)
        sampled = []
        for i in range(0, total, step):
            if len(sampled) >= sample_count:
                break
            c = chunks[i].copy()
            c.setdefault("score", 0.0)
            c.setdefault("source", "sample")
            sampled.append(c)

        top_matches = search(query, chunks, embeddings, model, top_k=5)

        seen = set()
        combined = []
        for c in top_matches + sampled:
            if c["text"] not in seen:
                seen.add(c["text"])
                c_copy = c.copy()
                c_copy.setdefault("score", 0.0)
                c_copy.setdefault("source", "semantic")
                combined.append(c_copy)
        return combined

    results = search(
        query,
        chunks,
        embeddings,
        model,
        top_k
    )
    return results


def is_module_count_question(query):
    """
    Check whether the user is asking for the number of modules.
    """
    query = query.lower()
    keywords = [
        "how many modules",
        "number of modules",
        "no of modules",
        "count of modules"
    ]
    return any(keyword in query for keyword in keywords)


def answer_module_count_question(pdf_path: str = None):
    """
    Answer a module-count question using direct document search on the active PDF.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return "No active PDF loaded."
    modules = find_module_headings(pdf_path)
    return (
        f"There are {len(modules)} modules in the PDF: "
        + ", ".join(modules)
        + "."
    )


def build_context(results):
    """
    Convert retrieved chunks into text context for Gemini.
    """
    # [S<n>] ids let the model say which chunks it used (see citations.py).
    context = "\n\n".join(
        f"[S{i}] Page {result['page']}:\n{result['text']}"
        for i, result in enumerate(results, start=1)
    )
    return context


def generate_suggested_questions(pages: list) -> list:
    """
    Generates 3 to 5 document-specific suggested study/inquiry questions
    based on the actual uploaded PDF content using Gemini.
    """
    if not pages:
        return [
            "Summarize the main topics in this document.",
            "What key concepts are discussed in this PDF?",
            "What important questions does this document answer?"
        ]

    sample_text = "\n\n".join(p["text"] for p in pages[:6])[:3500].strip()
    if not sample_text:
        return [
            "Summarize the main topics in this document.",
            "What key concepts are discussed in this PDF?",
            "What important questions does this document answer?"
        ]

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key in ["dummy_key_for_load", "AIzaSy_placeholder_key_for_load"]:
        return [
            "What are the key concepts covered in this document?",
            "Summarize the main topics discussed in this PDF.",
            "What important questions does this document answer?"
        ]

    prompt = f"""
Based on the following excerpt from an uploaded PDF document, generate 3 to 4 concise, practical, and highly relevant study/inquiry questions that a user would want to ask about this specific document.

DOCUMENT EXCERPT:
{sample_text}

INSTRUCTIONS:
- Return 3 to 4 questions strictly tailored to the specific topics in the document above.
- Do not assume specific structure like course codes, modules, or faculty names unless present in the excerpt.
- Each question must be clear, natural, and end with a question mark.
- Output ONLY the questions, one per line. Do not include numbering, bullets, or headers.
"""

    models_to_try = [PRIMARY_MODEL, FALLBACK_MODEL]
    active_client = get_client()

    for m_name in models_to_try:
        try:
            response = active_client.models.generate_content(
                model=m_name,
                contents=prompt
            )
            if response and response.text:
                lines = [
                    line.strip().lstrip("1234567890.-*• ")
                    for line in response.text.strip().split("\n")
                    if line.strip()
                ]
                questions = [q for q in lines if len(q) > 8 and q.endswith("?")]
                if len(questions) >= 2:
                    return questions[:4]
        except Exception as error:
            logger.warning("Suggested-question generation failed (%s).", type(error).__name__)

    return [
        "What are the key concepts covered in this document?",
        "Summarize the main topics discussed in this PDF.",
        "What important questions does this document answer?"
    ]


def generate_answer(query, context, answer_memory=None):
    """
    Ask Gemini to answer using the retrieved PDF context.
    Provides clear, structured, and complete answers based on document content.
    """
    memory_section = ""
    if answer_memory and answer_memory.strip():
        memory_section = f"""
CRITICAL ANSWER PRESENTATION INSTRUCTIONS (USER ANSWER MEMORY):
{answer_memory.strip()}
---
"""

    prompt = f"""
You are an intelligent PDF Assistant. Answer the user's question clearly, directly, and accurately using the provided PDF context excerpt below.

CRITICAL INSTRUCTIONS:
1. DIRECT & STRAIGHT ANSWER FIRST: When the user asks a direct question (e.g. "what is the problem statement", "what is the definition", "who is the author", "what are the main goals"), PROVIDE THE DIRECT, STRAIGHTFORWARD ANSWER IMMEDIATELY in the very first sentence or first bullet point. Never beat around the bush or provide verbose background before answering the question itself.
2. EXPLICIT DOCUMENT DECLARATIONS: If the document contains an explicit heading, title, or stated phrase matching the question (such as "Problem statement: ...", "Definition: ...", or "Objective: ..."), quote or state that exact statement prominently first.
3. CONVERSATIONAL QUERIES: If the user's question contains casual slang or conversational phrasing (e.g., "bro what is the problem statment"), interpret the core question ("what is the problem statement?") and answer it directly and professionally.
4. STRUCTURE & ANSWER MEMORY COMPLIANCE:
   - If User Answer Memory specifies a format (e.g., "in 3 bullet points only"):
     * Bullet 1 MUST deliver the direct, straight answer to the user's question (e.g. the exact Problem Statement as declared in the document).
     * Subsequent bullets should provide the core context, key risks/challenges, or breakdown as documented in the PDF.
   - Ground all statements strictly in the provided PDF excerpt. Do not invent or assume outside information.
5. SOURCE IDS: The excerpt is split into blocks labelled [S1], [S2], ... After your answer, add one final line in exactly this form listing ONLY the blocks whose text you actually used to answer the question: `SOURCES: S1,S3` (or `SOURCES: NONE`). Do not cite a block unless its text directly supports a specific claim in your answer. Do not mention the ids anywhere else in the answer.
6. RELEVANCE — CRITICAL: EVERY sentence or bullet in your answer must directly answer or clarify the user's question. Do NOT include facts about other topics (skills, hobbies, interests, unrelated experience, etc.) simply because they appear in the context. If the question has a single clear answer, give that answer concisely. Do not pad the answer with additional points from unrelated context blocks. If the context does not contain enough information to answer the question, say so.

{memory_section}
PDF CONTEXT EXCERPT:
{context}

USER QUESTION:
{query}
"""

    models_to_try = [
        PRIMARY_MODEL,
        FALLBACK_MODEL
    ]

    active_client = get_client()

    for model_name in models_to_try:
        try:
            print(f"\nGenerating answer with {model_name}...")

            response = active_client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            if response and response.text and response.text.strip():
                return response.text.strip()

        except Exception as error:
            logger.warning("Gemini PDF generation failed for %s (%s).", model_name, type(error).__name__)

            if model_name != FALLBACK_MODEL:
                print(
                    f"Trying fallback model: {FALLBACK_MODEL}..."
                )

            time.sleep(1)

    print("\nGemini models are temporarily unavailable.")
    return None


def generate_general_answer(query, answer_memory=None):
    """
    Ask Gemini to answer using its general knowledge.
    """
    current_date = datetime.now(timezone.utc).date().isoformat()
    memory_section = ""
    if answer_memory and answer_memory.strip():
        memory_section = f"""
CRITICAL ANSWER PRESENTATION INSTRUCTIONS (USER ANSWER MEMORY):
Format and structure your answer strictly according to these presentation rules:
---
{answer_memory.strip()}
---
"""

    prompt = f"""
Answer the user's question using your general knowledge.

CURRENT DATE (UTC): {current_date}

The answer is not available in the provided PDF.

Do not claim that the information came from the PDF.

FACTUAL RELIABILITY:
- Use the current date as temporal context for time-sensitive questions.
- Do not infer whether an event has occurred from its typical schedule alone.
- Do not invent dates, winners, outcomes, or other factual details.
- Do not claim an event has not occurred or been announced without reliable basis.
- Distinguish established facts from uncertainty. If you cannot answer reliably, say so clearly instead of guessing.
{memory_section}
USER QUESTION:
{query}
"""

    models_to_try = [
        PRIMARY_MODEL,
        FALLBACK_MODEL
    ]

    active_client = get_client()

    for model_name in models_to_try:
        try:
            print(f"\nGenerating general answer with {model_name}...")

            response = active_client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            if response and response.text and response.text.strip():
                return response.text.strip()

        except Exception as error:
            logger.warning("Gemini general generation failed for %s (%s).", model_name, type(error).__name__)

            if model_name != FALLBACK_MODEL:
                print(
                    f"Trying fallback model: {FALLBACK_MODEL}..."
                )

            time.sleep(1)

    print("\nGemini models are temporarily unavailable.")
    return None
