import hashlib


def get_file_hash(file_path):
    """
    Create a SHA-256 hash for the given file.

    The hash acts like a fingerprint for the PDF.
    """

    digest = hashlib.sha256()
    with open(file_path, "rb") as file:
        for file_chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(file_chunk)

    return digest.hexdigest()
