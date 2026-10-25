import threading
import time
import unittest
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import embedder


class EmbeddingModelLifecycleTests(unittest.TestCase):
    def test_concurrent_first_requests_load_one_model_instance(self):
        previous_model = embedder._model
        with embedder._model_load_lock:
            embedder._model = None
        instances = []
        instances_lock = threading.Lock()

        def build_model(name, **kwargs):
            time.sleep(0.03)
            instance = object()
            with instances_lock:
                instances.append((name, instance))
            return instance

        try:
            with mock.patch.object(embedder, "SentenceTransformer", side_effect=build_model):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    models = list(pool.map(lambda _: embedder.get_model(), range(8)))
            self.assertEqual(len(instances), 1)
            self.assertTrue(all(model is models[0] for model in models))
        finally:
            with embedder._model_load_lock:
                embedder._model = previous_model

    def test_model_inference_is_serialized_with_small_batches(self):
        state_lock = threading.Lock()
        active_calls = 0
        peak_calls = 0
        observed_kwargs = []

        class FakeModel:
            def encode(self, texts, **kwargs):
                nonlocal active_calls, peak_calls
                with state_lock:
                    active_calls += 1
                    peak_calls = max(peak_calls, active_calls)
                    observed_kwargs.append(kwargs)
                time.sleep(0.02)
                with state_lock:
                    active_calls -= 1
                return texts

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(
                lambda _: embedder.encode_texts(["query"], model=FakeModel()),
                range(8),
            ))

        self.assertEqual(peak_calls, 1)
        self.assertEqual(results, [["query"]] * 8)
        self.assertTrue(all(kwargs["batch_size"] == 8 for kwargs in observed_kwargs))
        self.assertTrue(all(kwargs["show_progress_bar"] is False for kwargs in observed_kwargs))


if __name__ == "__main__":
    unittest.main()
