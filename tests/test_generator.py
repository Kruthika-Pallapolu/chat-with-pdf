import unittest
from datetime import datetime, timezone
import os
import sys
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import generator


class GeneralAnswerPromptTests(unittest.TestCase):
    def test_client_uses_configured_http_timeout(self):
        with mock.patch.object(generator.genai, "Client") as client_factory:
            generator.get_client()

        options = client_factory.call_args.kwargs["http_options"]
        self.assertEqual(options.timeout, generator.GEMINI_TIMEOUT_MS)
        self.assertGreater(options.timeout, 0)

    def _capture_prompt(self):
        captured = []

        def generate_content(*, model, contents):
            captured.append(contents)
            return SimpleNamespace(text="I cannot answer reliably.")

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        frozen_now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        with mock.patch.object(generator, "datetime") as clock, mock.patch.object(
            generator, "get_client", return_value=client
        ):
            clock.now.return_value = frozen_now
            answer = generator.generate_general_answer("Who won the Nobel Prize in Literature?")

        self.assertEqual(answer, "I cannot answer reliably.")
        self.assertEqual(len(captured), 1)
        clock.now.assert_called_once_with(timezone.utc)
        return captured[0]

    def test_prompt_uses_current_server_date_not_stale_date(self):
        prompt = self._capture_prompt()

        self.assertIn("CURRENT DATE (UTC): 2026-10-24", prompt)
        self.assertNotIn("October 2025", prompt)
        self.assertNotIn("prior to October 2025", prompt)

    def test_prompt_requires_uncertainty_for_unreliable_time_sensitive_facts(self):
        prompt = self._capture_prompt()

        self.assertIn("Do not infer whether an event has occurred from its typical schedule alone.", prompt)
        self.assertIn("Do not claim an event has not occurred or been announced without reliable basis.", prompt)
        self.assertIn("If you cannot answer reliably, say so clearly instead of guessing.", prompt)


if __name__ == "__main__":
    unittest.main()