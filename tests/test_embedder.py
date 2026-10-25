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

        def build_model(name):
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


if __name__ == "__main__":
    unittest.main()
