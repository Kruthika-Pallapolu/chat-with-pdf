
import threading

from sentence_transformers import SentenceTransformer
from pdf_loader import extract_text
from chunker import chunk_text


_model = None
_model_load_lock = threading.Lock()


def get_model():
    """Load the embedding model once, including under concurrent first requests."""
    global _model
    if _model is None:
        with _model_load_lock:
            if _model is None:
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def create_embeddings(chunks):
    texts = [chunk["text"] for chunk in chunks]
    embeddings = get_model().encode(texts)
    return embeddings


if __name__ == "__main__":
    pages = extract_text("document.pdf")
    chunks = chunk_text(pages)
    embeddings = create_embeddings(chunks)

    print("Number of chunks:", len(chunks))
    print("Number of embeddings:", len(embeddings))
    print("Embedding dimensions:", len(embeddings[0]))
