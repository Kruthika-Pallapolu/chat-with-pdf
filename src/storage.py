import hashlib


def get_file_hash(file_path):
    """
    Create a SHA-256 hash for the given file.

    The hash acts like a fingerprint for the PDF.
    """

    with open(file_path, "rb") as file:
        file_bytes = file.read()

    return hashlib.sha256(file_bytes).hexdigest()