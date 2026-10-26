
import os
import logging
import threading

_thread_limit = max(1, int(os.getenv("CWP_NATIVE_THREAD_LIMIT", "1")))
for _thread_env in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_thread_env, str(_thread_limit))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import torch
torch.set_num_threads(_thread_limit)
try:
    torch.set_num_interop_threads(_thread_limit)
except RuntimeError:
    # The inter-op pool can only be configured before another library starts using it.
    pass

from sentence_transformers import SentenceTransformer
from pdf_loader import extract_text
from chunker import chunk_text


_model = None
_model_load_lock = threading.Lock()
_model_inference_lock = threading.Lock()
DEFAULT_EMBEDDING_BATCH_SIZE = 8
SUPPORTED_EMBEDDING_BATCH_SIZES = frozenset((8, 12))
logger = logging.getLogger("cwp")


def _parse_embedding_batch_size(raw_value):
    try:
        batch_size = int(raw_value)
    except (TypeError, ValueError):
        logger.warning("Invalid CWP_EMBEDDING_BATCH_SIZE; using safe default 8.")
        return DEFAULT_EMBEDDING_BATCH_SIZE
    if batch_size not in SUPPORTED_EMBEDDING_BATCH_SIZES:
        logger.warning("Unsupported CWP_EMBEDDING_BATCH_SIZE; using safe default 8.")
        return DEFAULT_EMBEDDING_BATCH_SIZE
    return batch_size


def _configured_embedding_batch_size():
    return _parse_embedding_batch_size(os.getenv("CWP_EMBEDDING_BATCH_SIZE", "8"))


EMBEDDING_BATCH_SIZE = _configured_embedding_batch_size()


def get_model():
    """Load the embedding model once, including under concurrent first requests."""
    global _model
    if _model is None:
        with _model_load_lock:
            if _model is None:
                _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    return _model


def encode_texts(texts, model=None):
    """Serialize CPU inference to bound peak memory across sessions and request types."""
    selected_model = model if model is not None else get_model()
    with _model_inference_lock:
        return selected_model.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            show_progress_bar=False,
        )


def create_embeddings(chunks):
    texts = [chunk["text"] for chunk in chunks]
    return encode_texts(texts)


if __name__ == "__main__":
    pages = extract_text("document.pdf")
    chunks = chunk_text(pages)
    embeddings = create_embeddings(chunks)

    print("Number of chunks:", len(chunks))
    print("Number of embeddings:", len(embeddings))
    print("Embedding dimensions:", len(embeddings[0]))
