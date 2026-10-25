import os, sys, types, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from citations import parse_sources_line, find_evidence, build_citations

CH1 = ("Records must be retained for seven years after account closure. "
       "Archived records are reviewed annually by the compliance team.")
CH2 = "The cafeteria opens at 8 am and closes at 4 pm on weekdays. Parking is free for staff."
CH3 = "Quarterly revenue growth targets are set by the finance committee each January."
RESULTS = [{"page": 3, "text": CH1, "score": .9}, {"page": 5, "text": CH2, "score": .8}, {"page": 7, "text": CH3, "score": .1}]

class ParseSources(unittest.TestCase):
    def test_valid_ids_and_strip(self):
        a, ids, rej = parse_sources_line("Seven years.\n\nSOURCES: S1,S3", 3)
        self.assertEqual((a, ids, rej), ("Seven years.", [0, 2], []))
    def test_out_of_range_and_duplicates_rejected(self):
        a, ids, rej = parse_sources_line("x\nSOURCES: S2, S9, S2, S0", 3)
        self.assertEqual(ids, [1]); self.assertEqual(rej, ["S9", "S0"]); self.assertEqual(a, "x")
    def test_markdown_wrapped_label(self):
        a, ids, _ = parse_sources_line("Body\n**SOURCES: S1**", 2)
        self.assertEqual((a, ids), ("Body", [0]))
    def test_none(self):
        a, ids, _ = parse_sources_line("Body\nSOURCES: NONE", 2)
        self.assertEqual((a, ids), ("Body", []))
    def test_missing_line_leaves_answer_untouched(self):
        a, ids, _ = parse_sources_line("Body only", 2); self.assertEqual((a, ids), ("Body only", []))
    def test_body_sentence_starting_with_sources_is_not_stripped(self):
        txt = "Sources: the policy says X.\nMore text after."
        a, ids, _ = parse_sources_line(txt, 2); self.assertEqual((a, ids), (txt, []))
    def test_invented_ids_in_prose_are_ignored(self):
        a, ids, _ = parse_sources_line("As S1 says...\nSOURCES: S2", 2); self.assertEqual(ids, [1])

class Evidence(unittest.TestCase):
    def test_supported_sentence_is_found_not_whole_chunk(self):
        ev = find_evidence("Records must be retained for seven years after account closure.", CH1)
        self.assertIsNotNone(ev)
        self.assertIn("seven years", ev["text"]); self.assertNotIn("compliance", ev["text"])
    def test_light_paraphrase_with_verbatim_run(self):
        ev = find_evidence("According to the document, records must be retained for seven years after the account is closed.", CH1)
        self.assertIsNotNone(ev); self.assertIn("seven years", ev["text"])
    def test_unrelated_answer_gives_no_evidence(self):
        self.assertIsNone(find_evidence("The weather tomorrow will be sunny with mild wind.", CH1))
    def test_pure_paraphrase_without_shared_run_gives_none(self):
        self.assertIsNone(find_evidence("Keep documentation about customers for seven years once they leave.", CH1))
    def test_few_tokens_not_enough(self):
        self.assertIsNone(find_evidence("seven years", CH1))
    def test_picks_the_supporting_chunk_sentence_in_multi_sentence_chunk(self):
        ev = find_evidence("Archived records are reviewed annually by the compliance team.", CH1)
        self.assertIn("reviewed annually", ev["text"]); self.assertNotIn("seven years", ev["text"])

class Build(unittest.TestCase):
    ANSWER = "Records must be retained for seven years after account closure."
    def test_high_score_chunk_that_is_not_cited_gets_no_citation(self):
        c = build_citations(self.ANSWER, RESULTS, [], None); self.assertEqual(c, [])
    def test_cited_but_unsupported_chunk_has_no_evidence(self):
        c = build_citations(self.ANSWER, RESULTS, [2], None)   # model cites S3 (revenue chunk)
        self.assertEqual(len(c), 1); self.assertFalse(c[0]["evidence_verified"]); self.assertIsNone(c[0]["evidence"]); self.assertEqual(c[0]["page"], 7)
    def test_cited_and_supported(self):
        c = build_citations(self.ANSWER, RESULTS, [0], None)
        self.assertTrue(c[0]["evidence_verified"]); self.assertEqual(c[0]["source_id"], "S1"); self.assertEqual(c[0]["page"], 3)
    def test_out_of_range_index_ignored(self):
        self.assertEqual(build_citations(self.ANSWER, RESULTS, [9], None), [])
    def test_position_hint_only_when_chunk_unique_in_page(self):
        pt = ["", "", "intro text. " + CH1 + " outro text that is long"]
        c = build_citations(self.ANSWER, RESULTS, [0], pt); h = c[0]["position_hint"]
        self.assertIsNotNone(h); self.assertTrue(0 < h < 1)
        pt2 = ["", "", CH1 + " " + CH1]
        self.assertIsNone(build_citations(self.ANSWER, RESULTS, [0], pt2)[0]["position_hint"])
        self.assertIsNone(build_citations(self.ANSWER, RESULTS, [0], None)[0]["position_hint"])

# ---- integration: real server.chat() with heavy deps stubbed -------------
def _load_server(retrieve_results, model_answer):
    stub = lambda name, **kw: sys.modules.setdefault(name, types.ModuleType(name))
    fa = types.ModuleType("fastapi")
    class HTTPException(Exception):
        def __init__(s, status_code=500, detail=""): s.status_code, s.detail = status_code, detail
    class FastAPI:
        def __init__(s, *a, **k): pass
        def add_middleware(s, *a, **k): pass
        def mount(s, *a, **k): pass
        def on_event(s, *a): return lambda f: f
        def __getattr__(s, n): return lambda *a, **k: (lambda f: f)
    fa.FastAPI, fa.HTTPException, fa.File, fa.UploadFile, fa.Form, fa.Request = FastAPI, HTTPException, lambda *a, **k: None, object, lambda *a, **k: None, object
    sys.modules["fastapi"] = fa
    for n, attrs in {"fastapi.exceptions": {"RequestValidationError": type("RequestValidationError", (Exception,), {})},
                     "fastapi.middleware": {}, "fastapi.middleware.cors": {"CORSMiddleware": object},
                     "fastapi.staticfiles": {"StaticFiles": lambda **k: None},
                     "fastapi.responses": {"FileResponse": object, "JSONResponse": lambda **k: k, "Response": object}}.items():
        m = types.ModuleType(n); [setattr(m, k, v) for k, v in attrs.items()]; sys.modules[n] = m
    for n, attrs in {"pdf_loader": {"extract_text": lambda p: []}, "chunker": {"chunk_text": lambda p: []},
                     "embedder": {"create_embeddings": lambda c: None},
                     "storage": {k: (lambda *a, **kw: "") for k in ["save_index","load_index","get_file_hash","save_answer_memory","load_answer_memory","clear_answer_memory"]},
                     "document_search": {"find_module_headings": lambda p: [], "get_structural_answer": lambda q, p: None}}.items():
        m = types.ModuleType(n); [setattr(m, k, v) for k, v in attrs.items()]; sys.modules[n] = m
    gen = types.ModuleType("generator")
    gen.retrieve = lambda q, c, e: retrieve_results
    gen.generate_answer = lambda q, ctx, answer_memory=None: model_answer
    gen.generate_general_answer = lambda q, answer_memory=None: "general"
    gen.generate_suggested_questions = lambda p: []
    gen.is_module_count_question = lambda q: False
    gen.answer_module_count_question = lambda p=None: ""
    gen.build_context = lambda r: ""
    gen.get_client = lambda: None
    sys.modules["generator"] = gen
    sys.modules.pop("server", None)
    import server; return server

class ServerChat(unittest.TestCase):
    def _chat(self, model_answer, page_texts=None):
        srv = _load_server(RESULTS, model_answer)
        srv._get_document_state = lambda _sid: srv.DocumentState(
            filename="test.pdf",
            pdf_path="x.pdf",
            chunks=[1],
            embeddings=None,
            page_texts=page_texts or [],
            is_ready=True,
        )
        srv.get_session_store = lambda: type("Preferences", (), {
            "get_preferences": lambda _self, _sid: ("", [])
        })()
        srv.os.path.exists = lambda p: True
        return srv._chat(srv.QuestionRequest(question="how long are records kept?"), "0123456789abcdef0123456789abcdef")
    def test_valid_citation_flows_to_response(self):
        r = self._chat("Records must be retained for seven years after account closure.\nSOURCES: S1")
        self.assertNotIn("SOURCES", r["answer"]); self.assertEqual(r["sources"], [3])
        self.assertEqual(len(r["citations"]), 1); self.assertTrue(r["citations"][0]["evidence_verified"])
        self.assertEqual(r["citations"][0]["page"], 3); self.assertEqual(len(r["retrieved_chunks"]), 3)
    def test_invented_id_gives_no_citation(self):
        r = self._chat("Records must be retained for seven years after account closure.\nSOURCES: S9")
        self.assertEqual(r["answer"], "Records must be retained for seven years after account closure.")
        self.assertEqual(r["citations"], [])
        self.assertEqual(r["sources"], [])
    def test_missing_sources_line_gives_no_citation_even_though_chunk0_scores_highest(self):
        r = self._chat("Records must be retained for seven years after account closure.")
        self.assertEqual(r["answer"], "Records must be retained for seven years after account closure.")
        self.assertEqual(r["citations"], [])
        self.assertEqual(r["sources"], [])
    def test_wrong_chunk_cited_is_not_verified(self):
        r = self._chat("Records must be retained for seven years after account closure.\nSOURCES: S3")
        self.assertEqual(len(r["citations"]), 1)
        self.assertFalse(r["citations"][0]["evidence_verified"])
        self.assertIsNone(r["citations"][0]["evidence"])
        self.assertEqual(r["sources"], [])
    def test_insufficient_pdf_evidence_requires_explicit_user_fallback(self):
        srv = _load_server([], "ignored")
        srv._get_document_state = lambda _sid: srv.DocumentState(
            filename="test.pdf", pdf_path="x.pdf", chunks=[1], is_ready=True
        )
        srv.get_session_store = lambda: type("Preferences", (), {
            "get_preferences": lambda _self, _sid: ("", [])
        })()
        srv.os.path.exists = lambda p: True
        r = srv._chat(
            srv.QuestionRequest(question="What is the hidden policy from the PDF?"),
            "0123456789abcdef0123456789abcdef",
        )
        self.assertIsNone(r["answer"])
        self.assertTrue(r["requires_fallback"])
        self.assertIn("general knowledge", r["fallback_prompt"].lower())
        self.assertEqual(r["sources"], [])
    def test_no_information_wording_requires_explicit_user_fallback(self):
        r = self._chat("The provided PDF excerpt does not contain any information about this question.")
        self.assertIsNone(r["answer"])
        self.assertTrue(r["requires_fallback"])
        self.assertEqual(r["sources"], [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
