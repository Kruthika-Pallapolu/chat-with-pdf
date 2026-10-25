import fitz


def extract_text(pdf_path):
    pdf = fitz.open(pdf_path)

    pages = []

    for page_number, page in enumerate(pdf, start=1):
        text = page.get_text()

        pages.append({
            "page": page_number,
            "text": text
        })

    pdf.close()

    return pages


if __name__ == "__main__":
    pages = extract_text("data/document.pdf")

    for page in pages:
        print(f"\n--- Page {page['page']} ---")
        print(page["text"])