from pdf_loader import extract_text


def chunk_text(pages, chunk_size=500, overlap=50):
    """
    Split PDF text into chunks while trying to preserve
    natural boundaries such as line breaks and sentences.
    """

    chunks = []

    for page in pages:
        text = page["text"]
        page_number = page["page"]

        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # If we are not at the end of the page,
            # try to move the boundary to a natural break.
            if end < len(text):

                # Look for the nearest newline before the limit.
                newline_position = text.rfind("\n", start, end)

                if newline_position > start:
                    end = newline_position

                else:
                    # If no newline is available,
                    # look for the nearest sentence-ending punctuation.
                    sentence_positions = [
                        text.rfind(".", start, end),
                        text.rfind("?", start, end),
                        text.rfind("!", start, end)
                    ]

                    sentence_position = max(sentence_positions)

                    if sentence_position > start:
                        end = sentence_position + 1

            chunk = text[start:end].strip()

            if chunk:
                chunks.append({
                    "page": page_number,
                    "text": chunk
                })

            # Move forward while keeping overlap.
            next_start = end - overlap

            # Prevent the loop from getting stuck.
            if next_start <= start:
                next_start = end

            start = next_start

    return chunks


if __name__ == "__main__":
    pages = extract_text("document.pdf")

    chunks = chunk_text(pages)

    print("Number of chunks:", len(chunks))
    print("\nFirst chunk:\n")
    print(chunks[0])