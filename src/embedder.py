from sentence_transformers import SentenceTransformer
from pdf_loader import extract_text
from chunker import chunk_text


model = SentenceTransformer("all-MiniLM-L6-v2")


def create_embeddings(chunks):
    texts = [chunk["text"] for chunk in chunks]

    embeddings = model.encode(texts)

    return embeddings


if __name__ == "__main__":
    pages = extract_text("document.pdf")

    chunks = chunk_text(pages)

    embeddings = create_embeddings(chunks)

    print("Number of chunks:", len(chunks))
    print("Number of embeddings:", len(embeddings))
    print("Embedding dimensions:", len(embeddings[0]))