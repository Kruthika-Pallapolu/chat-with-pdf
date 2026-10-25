import fitz


def extract_text(pdf_path):
    pages = []
    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            pages.append({
                "page": page_number,
                "text": page.get_text()
            })

    return pages


if __name__ == "__main__":
    pages = extract_text("data/document.pdf")

    for page in pages:
        print(f"\n--- Page {page['page']} ---")
        print(page["text"])
