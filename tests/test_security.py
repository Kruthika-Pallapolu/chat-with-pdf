import os
import tempfile
import time
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import server


class ApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch.object(server, "DATA_DIR", self.temp_dir.name),
            mock.patch.object(server, "IS_PRODUCTION", True),
        ]
        for patcher in self.patches:
            patcher.start()
        server._session_store_instance = None
        server._session_store_path = None
        self.client = TestClient(server.app, base_url="https://testserver", headers={"Origin": "https://testserver"})

    def tearDown(self):
        self.client.close()
        for patcher in reversed(self.patches):
            patcher.stop()
        server._session_store_instance = None
        server._session_store_path = None
        self.temp_dir.cleanup()

    def test_session_cookie_is_random_http_only_secure_and_same_site(self):
        response = self.client.get("/api/status")
        cookie = response.headers["set-cookie"].lower()

        self.assertEqual(response.status_code, 200)
        self.assertIn("httponly", cookie)
        self.assertIn("secure", cookie)
        self.assertIn("samesite=lax", cookie)
        self.assertGreaterEqual(len(self.client.cookies.get("cwp_session")), 40)

    def test_invalid_cookie_is_rejected_and_cannot_select_another_session(self):
        response = self.client.get("/api/status", headers={"Cookie": "cwp_session=" + "A" * 43})

        self.assertEqual(response.status_code, 401)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/api/status").json()["status"], "no_document")
        self.assertEqual(self.client.get("/api/pdf").status_code, 404)

    def test_request_supplied_gemini_key_is_rejected_without_environment_mutation(self):
        before = os.environ.get("GEMINI_API_KEY")
        payload = {"question": "Who won?", "api_key": "not-a-real-key"}

        chat_response = self.client.post("/api/chat", json=payload)
        fallback_response = self.client.post("/api/chat/fallback", json=payload)

        self.assertEqual(chat_response.status_code, 422)
        self.assertEqual(fallback_response.status_code, 422)
        self.assertNotIn("not-a-real-key", chat_response.text)
        self.assertNotIn("not-a-real-key", fallback_response.text)
        self.assertEqual(os.environ.get("GEMINI_API_KEY"), before)

    def test_cross_origin_mutation_is_rejected(self):
        response = self.client.post(
            "/api/session/logout",
            headers={"Origin": "https://attacker.invalid"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Cross-origin request rejected", response.text)

    def test_mutating_request_without_origin_is_rejected(self):
        client = TestClient(server.app, base_url="https://testserver")
        try:
            response = client.post("/api/session/logout")
        finally:
            client.close()
        self.assertEqual(response.status_code, 403)
        self.assertIn("Request origin is required", response.text)

    def test_unconfigured_host_header_is_rejected(self):
        response = self.client.get("/api/status", headers={"Host": "attacker.invalid"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Request host is not allowed", response.text)

    def test_invalid_cookies_cannot_bypass_session_creation_rate_limit(self):
        same_origin = {"Origin": "https://testserver"}
        first = self.client
        second = TestClient(server.app, base_url="https://testserver", headers=same_origin)
        third = TestClient(server.app, base_url="https://testserver", headers=same_origin)
        now = [120.0]
        try:
            with mock.patch.dict(os.environ, {"MAX_NEW_SESSIONS_PER_MINUTE": "1"}), \
                 mock.patch("session_store.time.time", side_effect=lambda: now[0]):
                self.assertEqual(first.get("/api/status").status_code, 200)
                denied = second.get("/api/status")
                self.assertEqual(denied.status_code, 429)
                invalid_cookie = third.get("/api/status", headers={"Cookie": "cwp_session=" + "B" * 43})
                self.assertEqual(invalid_cookie.status_code, 401)
                now[0] += 60
                self.assertEqual(third.get("/api/status").status_code, 200)
        finally:
            second.close()
            third.close()

    def test_static_allowlist_hides_backup_and_test_files(self):
        index = self.client.get("/")
        self.assertEqual(index.status_code, 200)
        self.assertIn('href="/static/cwp-favicon.svg?v=2"', index.text)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)
        self.assertEqual(self.client.get("/static/cwp-favicon.svg").status_code, 200)
        self.assertEqual(self.client.get("/static/share.js").status_code, 200)
        self.assertEqual(self.client.get("/static/share.css").status_code, 200)
        self.assertEqual(self.client.get("/static/share.html").status_code, 404)
        self.assertEqual(self.client.get("/static/app.js.backup").status_code, 404)
        self.assertEqual(self.client.get("/static/test.pdf").status_code, 404)
        self.assertEqual(self.client.get("/static/../.env").status_code, 404)

    def test_shared_conversation_is_durable_read_only_and_isolated_from_fresh_session(self):
        self.client.get("/api/status")
        conversations = [
            {
                "id": "conv_123456",
                "title": "Shared notes",
                "messages": [
                    {"sender": "user", "text": "Question with code?", "session_id": "must-not-share"},
                    {"sender": "assistant", "text": "Here is the full answer:\n```python\nprint(42)\n```", "internal_prompt": "must-not-share", "sources": [{"page": 4}]},
                ],
            },
            {
                "id": "conv_654321",
                "title": "Private conversation",
                "messages": [{"sender": "assistant", "text": "private other conversation content"}],
            },
        ]
        saved = self.client.put("/api/conversations", json={"conversations": conversations, "document_hash": None})
        self.assertEqual(saved.status_code, 200)

        created = self.client.post("/api/conversations/conv_123456/share")
        self.assertEqual(created.status_code, 200)
        share_path = created.json()["share_path"]
        share_id = share_path.rsplit("/", 1)[-1]
        self.assertRegex(share_id, r"^[A-Za-z0-9_-]{43}$")
        self.assertEqual(self.client.post("/api/conversations/conv_654321/share").status_code, 200)

        # Reopen the SQLite-backed store as a process restart would, and read from a fresh session.
        server._session_store_instance = None
        server._session_store_path = None
        fresh = TestClient(server.app, base_url="https://testserver", headers={"Origin": "https://testserver"})
        try:
            landing = fresh.get("/")
            self.assertEqual(landing.status_code, 200)
            self.assertTrue(fresh.cookies.get("cwp_session"))
            page = fresh.get(share_path)
            self.assertEqual(page.status_code, 200)
            self.assertIn("/static/share.js", page.text)
            data = fresh.get(f"/shared/{share_id}")
            self.assertEqual(data.status_code, 200)
            self.assertEqual(data.json(), {
                "title": "Shared notes",
                "messages": [
                    {"sender": "user", "text": "Question with code?"},
                    {"sender": "assistant", "text": "Here is the full answer:\n```python\nprint(42)\n```"},
                ],
            })
            self.assertNotIn("private other conversation content", data.text)
            self.assertNotIn("must-not-share", data.text)
            self.assertNotIn("session_id", data.text)
            self.assertEqual(fresh.get("/shared/not-a-valid-id").status_code, 404)
            self.assertEqual(fresh.get("/share/not-a-valid-id").status_code, 404)
        finally:
            fresh.close()

    def test_conversation_share_rejects_unknown_conversation(self):
        self.client.get("/api/status")
        response = self.client.post("/api/conversations/conv_123/share")
        self.assertEqual(response.status_code, 404)

    def test_conversation_share_rejects_unapproved_message_fields(self):
        self.client.get("/api/status")
        saved = self.client.put("/api/conversations", json={
            "conversations": [{
                "id": "conv_123",
                "title": "Invalid transcript",
                "messages": [{"sender": "system", "text": "internal prompt"}],
            }],
            "document_hash": None,
        })
        self.assertEqual(saved.status_code, 200)
        response = self.client.post("/api/conversations/conv_123/share")
        self.assertEqual(response.status_code, 400)

    def test_mobile_workspace_uses_stacked_panels_and_keyboard_drawer(self):
        index = self.client.get("/").text
        self.assertIn('aria-controls="sidebarPanel"', index)
        self.assertIn('id="sidebarBackdrop"', index)
        self.assertIn('role="button" tabindex="0" aria-label="Choose a PDF to upload"', index)

        stylesheet = self.client.get("/static/style.css").text
        self.assertIn(".workspace-container.mode-split {\n        flex-direction: column;", stylesheet)
        self.assertIn("height: 100dvh", stylesheet)
        self.assertIn("env(safe-area-inset-bottom)", stylesheet)

        script = self.client.get("/static/app.js").text
        self.assertIn("event.key === 'Escape'", script)
        self.assertIn("setMobileSidebarOpen(false)", script)

    def test_guest_wording_and_simplified_settings_are_rendered(self):
        response = self.client.get("/")
        self.assertIn("Continue in Guest Mode", response.text)
        self.assertNotIn("Demo Mode", response.text)
        self.assertIn("Answer Style", response.text)
        self.assertNotIn('id="settingAiModel"', response.text)
        self.assertNotIn('id="settingAnswerMode"', response.text)
        self.assertNotIn('id="settingTopK"', response.text)
        self.assertIn('name="themeSelect"', response.text)

    def test_model_exception_does_not_reveal_internal_details(self):
        self.client.get("/api/status")
        state = server.DocumentState(
            filename="private.pdf",
            pdf_path="/private/internal/path.pdf",
            chunks=[{"page": 1, "text": "private document text"}],
            embeddings=None,
            page_texts=["private document text"],
            is_ready=True,
        )
        with mock.patch.object(server, "_get_document_state", return_value=state), \
             mock.patch.object(server, "retrieve", return_value=[{"page": 1, "text": "private document text", "score": 1.0}]), \
             mock.patch.object(server, "build_context", return_value="private document text"), \
             mock.patch.object(server, "generate_answer", side_effect=RuntimeError("secret at /private/internal/path.pdf")):
            response = self.client.post("/api/chat", json={"question": "Summarize it"})

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret", response.text)
        self.assertNotIn("/private/internal/path.pdf", response.text)
        self.assertNotIn("private document text", response.text)

    def test_general_fallback_is_labelled_and_has_no_pdf_citations(self):
        with mock.patch.object(server, "generate_general_answer", return_value="An uncertain answer."):
            response = self.client.post("/api/chat/fallback", json={"question": "A general question?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["source_label"], "Gemini general knowledge")
        self.assertFalse(response.json()["found_in_pdf"])
        self.assertNotIn("sources", response.json())
        self.assertNotIn("citations", response.json())

    def test_general_fallback_reports_rate_limit_without_leaking_provider_details(self):
        with mock.patch.object(server, "generate_general_answer", side_effect=RuntimeError("429 quota at /secret")):
            response = self.client.post("/api/chat/fallback", json={"question": "A general question?"})

        self.assertEqual(response.status_code, 429)
        self.assertIn("rate limit or quota", response.json()["detail"].lower())
        self.assertNotIn("/secret", response.text)

    def test_insufficient_pdf_answer_does_not_call_general_generator_implicitly(self):
        self.client.get("/api/status")
        with mock.patch.object(server, "_get_document_state", return_value=server.DocumentState(
            filename="session.pdf", pdf_path="/session/document.pdf", chunks=[{"page": 1, "text": "document evidence"}],
            embeddings=None, page_texts=["document evidence"], is_ready=True,
        )), mock.patch.object(server, "retrieve", return_value=[]), \
             mock.patch.object(server, "get_structural_answer", return_value=None), \
             mock.patch.object(server, "generate_general_answer") as general_answer:
            response = self.client.post("/api/chat", json={"question": "An absent question?"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["requires_fallback"])
        general_answer.assert_not_called()

    def test_chat_rate_limit_rejects_then_recovers_after_window(self):
        self.client.get("/api/status")
        fixed_time = [time.time()]
        with mock.patch.dict(os.environ, {"MAX_CHAT_PER_MINUTE": "1"}), \
             mock.patch("session_store.time.time", side_effect=lambda: fixed_time[0]):
            first = self.client.post("/api/chat", json={"question": "No PDF yet"})
            second = self.client.post("/api/chat", json={"question": "No PDF yet"})
            fixed_time[0] += 60
            third = self.client.post("/api/chat", json={"question": "No PDF yet"})

        self.assertEqual(first.status_code, 400)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(third.status_code, 400)


if __name__ == "__main__":
    unittest.main()
