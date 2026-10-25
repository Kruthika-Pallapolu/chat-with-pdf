import io
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import fitz
import numpy as np
from fastapi.testclient import TestClient

import server


def make_pdf(text):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    output = io.BytesIO()
    document.save(output)
    document.close()
    return output.getvalue()


class UploadIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch.object(server, "DATA_DIR", self.temp_dir.name),
            mock.patch.object(server, "IS_PRODUCTION", True),
            mock.patch.object(server, "MAX_PDF_BYTES", 1024 * 1024),
            mock.patch.object(server, "MAX_PDF_PAGES", 5),
            mock.patch.object(server, "create_embeddings", side_effect=lambda chunks: np.ones((len(chunks), 4), dtype=np.float32)),
            mock.patch.object(server, "generate_suggested_questions", return_value=[]),
            mock.patch.object(server, "find_module_headings", return_value=[]),
        ]
        for patcher in self.patches:
            patcher.start()
        server._session_store_instance = None
        server._session_store_path = None

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        server._session_store_instance = None
        server._session_store_path = None
        self.temp_dir.cleanup()

    def client(self):
        return TestClient(server.app, base_url="https://testserver", headers={"Origin": "https://testserver"})

    def upload(self, client, filename, text):
        return client.post("/api/upload", files={"file": (filename, make_pdf(text), "application/pdf")})

    def pdf_text(self, client):
        response = client.get("/api/pdf")
        with fitz.open(stream=response.content, filetype="pdf") as document:
            return "\n".join(page.get_text() for page in document)

    def test_two_sessions_uploading_same_filename_remain_isolated(self):
        first, second = self.client(), self.client()
        first_response = self.upload(first, "same.pdf", "First visitor private fact.")
        second_response = self.upload(second, "same.pdf", "Second visitor private fact.")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertNotEqual(first.cookies.get("cwp_session"), second.cookies.get("cwp_session"))
        self.assertIn("First visitor", self.pdf_text(first))
        self.assertIn("Second visitor", self.pdf_text(second))
        self.assertNotIn("Second visitor", self.pdf_text(first))
        first_pdf_before_second_replacement = first.get("/api/pdf").content
        self.assertEqual(self.upload(second, "same.pdf", "Second replacement only.").status_code, 200)
        self.assertEqual(first.get("/api/pdf").content, first_pdf_before_second_replacement)
        self.assertEqual(second.delete("/api/document").status_code, 200)
        self.assertEqual(second.get("/api/pdf").status_code, 404)
        self.assertEqual(first.get("/api/pdf").content, first_pdf_before_second_replacement)

    def test_new_session_cannot_read_or_query_another_session_document(self):
        owner, stranger = self.client(), self.client()
        self.assertEqual(self.upload(owner, "private.pdf", "owner-only passage").status_code, 200)

        self.assertEqual(stranger.get("/api/pdf").status_code, 404)
        self.assertEqual(
            stranger.post("/api/chat", json={"question": "What does it say?"}).status_code,
            400,
        )
        stranger_pdf = stranger.get("/api/pdf")
        self.assertEqual(stranger_pdf.status_code, 404)
        self.assertNotIn("owner-only passage", stranger_pdf.text)

    def test_failed_replacement_preserves_existing_document(self):
        client = self.client()
        self.assertEqual(self.upload(client, "active.pdf", "original passage").status_code, 200)
        previous_bytes = client.get("/api/pdf").content
        with mock.patch.object(server, "_build_document_state", side_effect=ValueError("private path /secret")):
            response = self.upload(client, "active.pdf", "replacement passage")

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("/secret", response.text)
        self.assertEqual(client.get("/api/pdf").content, previous_bytes)

    def test_oversized_upload_is_rejected_before_processing(self):
        client = self.client()
        with mock.patch.object(server, "MAX_PDF_BYTES", 128):
            response = self.upload(client, "large.pdf", "x" * 1000)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["detail"], "PDF exceeds the configured upload size limit.")

    def test_page_limit_rejects_pdf_without_replacing_existing_file(self):
        client = self.client()
        self.assertEqual(self.upload(client, "existing.pdf", "existing data").status_code, 200)
        existing_pdf = client.get("/api/pdf").content
        many_pages = fitz.open()
        for _ in range(6):
            many_pages.new_page()
        payload = io.BytesIO()
        many_pages.save(payload)
        many_pages.close()
        with mock.patch.object(server, "MAX_PDF_PAGES", 5):
            response = client.post("/api/upload", files={"file": ("large.pdf", payload.getvalue(), "application/pdf")})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(client.get("/api/pdf").content, existing_pdf)

    def test_concurrent_visitors_get_separate_document_directories(self):
        clients = [self.client(), self.client()]
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda item: self.upload(item[0], "same.pdf", item[1]), zip(clients, ["A secret", "B secret"])))
        self.assertEqual([response.status_code for response in responses], [200, 200])
        self.assertIn("A secret", self.pdf_text(clients[0]))
        self.assertIn("B secret", self.pdf_text(clients[1]))

    def test_replacement_resets_only_that_sessions_conversations(self):
        first, second = self.client(), self.client()
        self.assertEqual(first.put("/api/conversations", json={"conversations": [{"id": "first"}]}).status_code, 200)
        self.assertEqual(second.put("/api/conversations", json={"conversations": [{"id": "second"}]}).status_code, 200)
        self.assertEqual(self.upload(first, "replacement.pdf", "new private content").status_code, 200)
        self.assertEqual(first.get("/api/conversations").json()["conversations"], [])
        stale_save = first.put("/api/conversations", json={
            "conversations": [{"id": "stale"}],
            "document_hash": None,
        })
        self.assertEqual(stale_save.status_code, 409)
        self.assertEqual(first.get("/api/conversations").json()["conversations"], [])
        self.assertEqual(second.get("/api/conversations").json()["conversations"], [{"id": "second"}])


if __name__ == "__main__":
    unittest.main()