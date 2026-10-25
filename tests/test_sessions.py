import os
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from session_store import SessionCapacityError, SessionNotFoundError, SessionStorageLimitError, SessionStore


class SessionStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SessionStore(self.temp_dir.name, ttl_seconds=300, max_sessions=3)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_opaque_token_resolves_only_to_its_server_record(self):
        first = self.store.resolve()
        same = self.store.resolve(first.token)
        second = self.store.resolve()

        self.assertTrue(first.created)
        self.assertFalse(same.created)
        self.assertEqual(first.session_id, same.session_id)
        self.assertNotEqual(first.session_id, second.session_id)
        self.assertNotEqual(first.token, second.token)
        self.assertEqual(len(first.token), 43)

    def test_session_preferences_are_isolated(self):
        first = self.store.resolve()
        second = self.store.resolve()
        self.store.set_answer_memory(first.session_id, "first visitor")
        self.store.set_conversations(first.session_id, [{"id": "first-conversation"}])

        first_memory, first_conversations = self.store.get_preferences(first.session_id)
        second_memory, second_conversations = self.store.get_preferences(second.session_id)

        self.assertEqual(first_memory, "first visitor")
        self.assertEqual(first_conversations, [{"id": "first-conversation"}])
        self.assertEqual(second_memory, "")
        self.assertEqual(second_conversations, [])

    def test_long_lived_token_rotates_without_changing_session(self):
        original = self.store.resolve()
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE sessions SET created_at = ? WHERE session_id = ?",
                (time.time() - 200, original.session_id),
            )

        rotated = self.store.resolve(original.token)

        self.assertTrue(rotated.rotated)
        self.assertFalse(rotated.created)
        self.assertEqual(rotated.session_id, original.session_id)
        self.assertNotEqual(rotated.token, original.token)
        replacement = self.store.resolve(rotated.token)
        self.assertEqual(replacement.session_id, original.session_id)
        with self.assertRaises(SessionNotFoundError):
            self.store.resolve(original.token)

    def test_expired_session_is_rejected_and_its_files_are_removed(self):
        old = self.store.resolve()
        old_dir = self.store.session_dir(old.session_id)
        old_dir.mkdir(exist_ok=True)
        with open(old_dir / "private.pdf", "wb") as file:
            file.write(b"fixture")
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE sessions SET last_seen = ? WHERE session_id = ?",
                (time.time() - 600, old.session_id),
            )
        self.store._last_cleanup = 0

        with self.assertRaises(SessionNotFoundError):
            self.store.resolve(old.token)
        self.assertFalse(old_dir.exists())

    def test_session_paths_reject_untrusted_identifiers(self):
        with self.assertRaises(ValueError):
            self.store.session_dir("../outside")

    def test_rate_limit_is_scoped_to_session_and_ip(self):
        first = self.store.resolve()
        second = self.store.resolve()

        self.assertTrue(self.store.allow_request(first.session_id, "192.0.2.1", "chat", 1))
        self.assertFalse(self.store.allow_request(first.session_id, "192.0.2.1", "chat", 1))
        self.assertTrue(self.store.allow_request(second.session_id, "192.0.2.2", "chat", 1))
        with self.store._connect() as connection:
            subjects = [row[0] for row in connection.execute("SELECT subject FROM rate_counters")]
        self.assertTrue(all("192.0.2." not in subject for subject in subjects))

    def test_ip_limited_session_creation_recovers_after_window(self):
        with mock.patch("session_store.time.time", return_value=120.0):
            self.assertTrue(self.store.allow_ip_request("192.0.2.1", "create", 1, 60))
            self.assertFalse(self.store.allow_ip_request("192.0.2.1", "create", 1, 60))
        with mock.patch("session_store.time.time", return_value=180.0):
            self.assertTrue(self.store.allow_ip_request("192.0.2.1", "create", 1, 60))

    def test_session_capacity_is_bounded(self):
        for _ in range(3):
            self.store.resolve()
        with self.assertRaises(SessionCapacityError):
            self.store.resolve()

    def test_session_and_total_storage_quotas_reject_without_corrupting_usage(self):
        self.store.max_session_bytes = 128
        self.store.max_total_bytes = 128
        first = self.store.resolve()
        second = self.store.resolve()

        self.assertEqual(self.store.set_document_bytes(first.session_id, 100), 0)
        with self.assertRaises(SessionStorageLimitError):
            self.store.set_document_bytes(second.session_id, 40)
        self.assertEqual(self.store.set_document_bytes(first.session_id, 80), 100)
        with self.assertRaises(SessionStorageLimitError):
            self.store.set_conversations(first.session_id, [{"text": "x" * 100}])

        with self.store._connect() as connection:
            usage = connection.execute(
                "SELECT document_bytes, history_bytes FROM session_storage WHERE session_id = ?",
                (first.session_id,),
            ).fetchone()
        self.assertEqual(usage, (80, 0))

    def test_storage_ledger_reconciles_existing_session_files(self):
        session = self.store.resolve()
        document_id = "a" * 32
        session_dir = self.store.session_dir(session.session_id)
        document_dir = session_dir / "documents" / document_id
        document_dir.mkdir(parents=True)
        (document_dir / "document.pdf").write_bytes(b"private-pdf-bytes")
        (session_dir / "active.json").write_text(json.dumps({"document_id": document_id}))
        self.store.set_conversations(session.session_id, [{"id": "history"}])
        with self.store._connect() as connection:
            connection.execute(
                "UPDATE session_storage SET document_bytes = 0 WHERE session_id = ?",
                (session.session_id,),
            )

        recovered = SessionStore(self.temp_dir.name, ttl_seconds=300, max_sessions=3)
        previous = recovered.set_document_bytes(session.session_id, 5)

        self.assertEqual(previous, len(b"private-pdf-bytes"))
        _, history = recovered.get_preferences(session.session_id)
        self.assertEqual(history, [{"id": "history"}])


if __name__ == "__main__":
    unittest.main()