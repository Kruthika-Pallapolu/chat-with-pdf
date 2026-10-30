import os
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import numpy as np

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
        self.assertTrue(all(kwargs["batch_size"] == embedder.EMBEDDING_BATCH_SIZE for kwargs in observed_kwargs))
        self.assertTrue(all(kwargs["show_progress_bar"] is False for kwargs in observed_kwargs))

    def test_embedding_batch_size_allows_benchmark_values_and_defaults_on_invalid_values(self):
        for raw_value, expected in (("4", 4), ("8", 8), ("12", 12), (" 12 ", 12)):
            with self.subTest(raw_value=raw_value):
                self.assertEqual(embedder._parse_embedding_batch_size(raw_value), expected)
        for raw_value in ("", "invalid", "0", "-1", "16"):
            with self.subTest(raw_value=raw_value):
                self.assertEqual(embedder._parse_embedding_batch_size(raw_value), 8)
        with mock.patch.dict(os.environ, {"CWP_EMBEDDING_BATCH_SIZE": "12"}):
            self.assertEqual(embedder._configured_embedding_batch_size(), 12)
        with mock.patch.dict(os.environ, {"CWP_EMBEDDING_BATCH_SIZE": "4"}):
            self.assertEqual(embedder._configured_embedding_batch_size(), 4)
        with mock.patch.dict(os.environ, {"CWP_EMBEDDING_BATCH_SIZE": "invalid"}):
            self.assertEqual(embedder._configured_embedding_batch_size(), 8)

    def test_encode_texts_uses_selected_batch_size(self):
        observed_kwargs = []

        class FakeModel:
            def encode(self, texts, **kwargs):
                observed_kwargs.append(kwargs)
                return texts

        with mock.patch.object(embedder, "EMBEDDING_BATCH_SIZE", 12):
            embedder.encode_texts(["query"], model=FakeModel())

        self.assertEqual(observed_kwargs[0]["batch_size"], 12)

    def test_create_embeddings_preserves_chunk_order_and_embedding_shape(self):
        received_texts = []
        observed_kwargs = []

        class FakeModel:
            def encode(self, texts, **kwargs):
                received_texts.extend(texts)
                observed_kwargs.append(kwargs)
                return np.arange(len(texts) * 4, dtype=np.float32).reshape(len(texts), 4)

        chunks = [
            {"page": 3, "text": "third chunk"},
            {"page": 1, "text": "first chunk"},
            {"page": 2, "text": "second chunk"},
        ]
        with mock.patch.object(embedder, "get_model", return_value=FakeModel()):
            embeddings = embedder.create_embeddings(chunks)

        self.assertEqual(received_texts, ["third chunk", "first chunk", "second chunk"])
        self.assertEqual(embeddings.shape, (3, 4))
        self.assertEqual(embeddings.dtype, np.float32)
        self.assertEqual(embeddings[:, 0].tolist(), [0.0, 4.0, 8.0])
        self.assertEqual(observed_kwargs[0]["batch_size"], embedder.EMBEDDING_BATCH_SIZE)
        self.assertFalse(observed_kwargs[0]["show_progress_bar"])
        self.assertNotIn("normalize_embeddings", observed_kwargs[0])

    def test_create_embeddings_for_empty_chunks_passes_empty_batch_through(self):
        observed_texts = []

        class FakeModel:
            def encode(self, texts, **kwargs):
                observed_texts.extend(texts)
                return np.empty((0, 4), dtype=np.float32)

        with mock.patch.object(embedder, "get_model", return_value=FakeModel()):
            embeddings = embedder.create_embeddings([])

        self.assertEqual(observed_texts, [])
        self.assertEqual(embeddings.shape[0], 0)
        self.assertEqual(embeddings.dtype, np.float32)


if __name__ == "__main__":
    unittest.main()
