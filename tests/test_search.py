import os
import sys
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
from search import search


class RelevanceFilteringTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            {"page": 1, "text": "The organization reviews annual compliance procedures."},
            {"page": 2, "text": "Employees receive scheduled training each quarter."},
        ]
        self.model = mock.Mock()
        self.model.encode.return_value = np.ones((1, 4))

    def test_below_threshold_semantic_matches_are_not_forced_into_context(self):
        with mock.patch("search.cosine_similarity", return_value=np.array([[0.10, 0.12]])):
            results = search("xylophone", self.chunks, np.ones((2, 4)), self.model)

        self.assertEqual(results, [])

    def test_semantic_match_above_existing_threshold_is_retained_without_keyword_match(self):
        with mock.patch("search.cosine_similarity", return_value=np.array([[0.31, 0.10]])):
            results = search("organization policy", self.chunks, np.ones((2, 4)), self.model)

        self.assertEqual([result["page"] for result in results], [1])


if __name__ == "__main__":
    unittest.main()
