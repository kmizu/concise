import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCORER = ROOT / "scripts/evaluate_responses.py"


class ResponseEvalTest(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCORER.is_file(), "Response scorer is missing")
        spec = importlib.util.spec_from_file_location("evaluate_responses", SCORER)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.case = {"id": "fact", "context": "", "prompt": "Australia's capital?", "rubric": "Answer Canberra.",
                     "checks": [{"label": "capital", "pattern": "Canberra"}], "max_characters": 30}

    def sample(self, text="Canberra.", review=None):
        result = {"case_id": "fact", "text": text}
        if review is not None:
            result["review"] = review
        return result

    def review(self, **overrides):
        return {"accurate": True, "complete": True, "readable": True,
                "unnecessary_question": False, "evidence": "Answers Canberra directly.", **overrides}

    def test_keyword_presence_is_not_semantic_success(self):
        score = self.module.score_answer(self.case, self.sample("It is not Canberra."))
        self.assertTrue(score["content_indicators_pass"])
        self.assertIsNone(score["quality_pass"])

    def test_short_wrong_answer_fails_even_when_keyword_matches(self):
        score = self.module.score_answer(self.case, self.sample("Not Canberra.", self.review(accurate=False)))
        self.assertTrue(score["length_target_pass"])
        self.assertFalse(score["quality_pass"])

    def test_unreviewed_answers_cannot_pass_quality(self):
        score = self.module.score_answer(self.case, self.sample())
        self.assertIsNone(score["quality_pass"])

    def test_complete_answer_can_exceed_a_nonbinding_length_target(self):
        score = self.module.score_answer(self.case, self.sample("Canberra. " * 8, self.review()))
        self.assertFalse(score["length_target_pass"])
        self.assertTrue(score["quality_pass"])

    def test_unnecessary_confirmation_fails_quality(self):
        score = self.module.score_answer(self.case, self.sample("Canberra?", self.review(unnecessary_question=True)))
        self.assertFalse(score["quality_pass"])

    def test_review_requires_real_booleans_and_evidence(self):
        for review in (self.review(accurate="true"), self.review(evidence=""), {"accurate": True}):
            with self.subTest(review=review), self.assertRaises(ValueError):
                self.module.score_answer(self.case, self.sample(review=review))

    def test_duplicate_and_missing_samples_are_rejected(self):
        for samples in ([], [self.sample(), self.sample()], [{"case_id": "unknown", "text": "X"}]):
            with self.subTest(samples=samples), self.assertRaises(ValueError):
                self.module.score_condition([self.case], samples)

    def test_summary_separates_quality_coverage_and_length(self):
        result = self.module.score_condition([self.case], [self.sample(review=self.review())])
        self.assertEqual(1, result["quality_passes"])
        self.assertEqual(1, result["reviewed"])
        self.assertEqual(1, result["content_indicator_passes"])
        self.assertEqual(9, result["characters"])

    def test_duplicate_case_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.module.score_condition([self.case, self.case], [self.sample()])

    def experiment(self, root, reviewed=True):
        def write(name, value):
            (root / name).write_text(json.dumps(value), encoding="utf8")
        write("cases.json", [self.case])
        write("answers.json", [self.sample()])
        (root / "rules.md").write_text("Rules\n", encoding="utf8")
        condition = {"rules_file": "rules.md", "rules_sha256": self.module.text_hash("Rules\n"),
                     "answers_file": "answers.json"}
        if reviewed:
            condition["reviews_file"] = "reviews.json"
            review = {"case_id": "fact", "text_sha256": self.module.text_hash("Canberra."), **self.review()}
            write("reviews.json", {"reviewer": "Independent test reviewer", "conditions": {"candidate": [review]}})
        write("experiment.json", {"cases_file": "cases.json",
              "cases_sha256": self.module.text_hash((root / "cases.json").read_text(encoding="utf8")),
              "collection": {"method": "synthetic unit-test fixture"}, "conditions": {"candidate": condition}})
        if reviewed:
            document = self.module.read_json(root / "reviews.json")
            document["source_fingerprint"] = self.module.experiment_fingerprint(
                self.module.read_json(root / "experiment.json"))
            write("reviews.json", document)
        return root / "experiment.json"

    def test_persisted_reviews_are_bound_to_the_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.experiment(root)
            self.assertEqual(1, self.module.score_experiment(manifest)["conditions"]["candidate"]["quality_passes"])
            (root / "answers.json").write_text(json.dumps([self.sample("Not Canberra.")]), encoding="utf8")
            with self.assertRaisesRegex(ValueError, "different answer"):
                self.module.score_experiment(manifest)

    def test_changed_cases_or_rules_invalidate_the_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in ("cases.json", "rules.md"):
                manifest = self.experiment(root)
                with (root / filename).open("a", encoding="utf8") as stream:
                    stream.write(" ")
                with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, "changed since collection"):
                    self.module.score_experiment(manifest)

    def test_review_provenance_and_hash_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mutation in ("provenance", "provenance_type", "hash", "duplicate", "missing"):
                manifest = self.experiment(root)
                reviews = self.module.read_json(root / "reviews.json")
                entries = reviews["conditions"]["candidate"]
                if mutation == "provenance":
                    reviews["reviewer"] = ""
                elif mutation == "provenance_type":
                    reviews["reviewer"] = True
                elif mutation == "hash":
                    del entries[0]["text_sha256"]
                elif mutation == "duplicate":
                    entries.append(entries[0])
                else:
                    entries.clear()
                (root / "reviews.json").write_text(json.dumps(reviews), encoding="utf8")
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    self.module.score_experiment(manifest)

    def test_paths_cannot_escape_the_experiment_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.experiment(root)
            for name in ("../outside.json", str(manifest.resolve())):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.module.contained_file(root, name)

    def test_quality_gate_rejects_unreviewed_and_failed_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.experiment(root, reviewed=False)
            def run(*extra):
                return subprocess.run([sys.executable, str(SCORER), str(manifest),
                                       "--require-quality", *extra], capture_output=True, text=True).returncode
            self.assertEqual(1, run())
            self.assertEqual(2, run("--condition", "unknown"))
            self.experiment(root)
            self.assertEqual(0, run("--condition", "candidate"))
            reviews = self.module.read_json(root / "reviews.json")
            reviews["conditions"]["candidate"][0]["accurate"] = False
            (root / "reviews.json").write_text(json.dumps(reviews), encoding="utf8")
            self.assertEqual(1, run())

    def test_prompt_only_collection_input_matches_the_suite(self):
        cases = self.module.read_json(ROOT / "evals/cases.json")
        prompts = self.module.read_json(ROOT / "evals/prompts.json")
        self.assertEqual([{key: case[key] for key in ("id", "language", "context", "prompt")}
                          for case in cases], prompts)

    def test_blind_review_mapping_cannot_be_reassigned(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import prepare_response_review as helper
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = self.experiment(root, reviewed=False)
                data = self.module.read_json(manifest)
                (root / "control.json").write_text(json.dumps([self.sample("Canberra is the capital.")]), encoding="utf8")
                data["conditions"]["control"] = {"rules_file": None, "rules_sha256": None, "answers_file": "control.json"}
                manifest.write_text(json.dumps(data), encoding="utf8")
                blind, key = helper.prepare(manifest, 42)
                decisions = {"reviewer": "Independent test reviewer", "review_input_sha256": self.module.text_hash(helper.serialize_json(blind)), "reviews": [
                    {"case_id": "fact", "variant": variant, **self.review()}
                    for variant in blind["cases"][0]["answers"]]}
                attached = helper.attach(manifest, key, decisions)
                self.assertEqual({"candidate", "control"}, set(attached["conditions"]))
                first, second = key["mapping"]
                first["variant"], second["variant"] = second["variant"], first["variant"]
                with self.assertRaisesRegex(ValueError, "mapping"):
                    helper.attach(manifest, key, decisions)
        finally:
            sys.path.pop(0)

    def test_stale_blind_decisions_cannot_be_attached_after_recapture(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import prepare_response_review as helper
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for changed in ("answer", "rules"):
                    manifest = self.experiment(root, reviewed=False)
                    blind, key = helper.prepare(manifest, 42)
                    decisions = {"reviewer": "Independent test reviewer",
                                 "review_input_sha256": self.module.text_hash(helper.serialize_json(blind)),
                                 "reviews": [{"case_id": "fact", "variant": "response-1", **self.review()}]}
                    if changed == "answer":
                        (root / "answers.json").write_text(json.dumps([self.sample("Sydney.")]), encoding="utf8")
                    else:
                        (root / "rules.md").write_text("New rules\n", encoding="utf8")
                        data = self.module.read_json(manifest)
                        data["conditions"]["candidate"]["rules_sha256"] = self.module.text_hash("New rules\n")
                        manifest.write_text(json.dumps(data), encoding="utf8")
                    _, new_key = helper.prepare(manifest, 42)
                    with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "reviewed input"):
                        helper.attach(manifest, new_key, decisions)
        finally:
            sys.path.pop(0)

    def test_updated_source_hashes_do_not_revalidate_old_reviews(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for changed in ("rules", "rubric"):
                manifest = self.experiment(root)
                data = self.module.read_json(manifest)
                if changed == "rules":
                    (root / "rules.md").write_text("Different rules\n", encoding="utf8")
                    data["conditions"]["candidate"]["rules_sha256"] = self.module.text_hash("Different rules\n")
                else:
                    cases = self.module.read_json(root / "cases.json")
                    cases[0]["rubric"] = "Give a different answer."
                    (root / "cases.json").write_text(json.dumps(cases), encoding="utf8")
                    data["cases_sha256"] = self.module.text_hash((root / "cases.json").read_text(encoding="utf8"))
                manifest.write_text(json.dumps(data), encoding="utf8")
                with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "source fingerprint"):
                    self.module.score_experiment(manifest)

    def test_recorded_candidate_matches_the_shipped_rules_and_report(self):
        self.assert_recorded_candidate(ROOT / "evals/pilot.json", ROOT / "evals/results.json")

    def test_recorded_claude_code_pilot_matches_the_shipped_rules_and_report(self):
        # The Claude Code pilot is recorded evidence, not a release gate: its
        # candidate passed 11 of 12, and the report says so. The test keeps the
        # record reproducible and bound to the shipped rules.
        scores = self.assert_recorded_candidate(
            ROOT / "evals/claude-code/pilot.json", ROOT / "evals/claude-code/results.json", require_all_pass=False)
        for condition in scores["conditions"].values():
            self.assertEqual(12, condition["reviewed"])
            self.assertFalse(condition["unreviewed"])

    def assert_recorded_candidate(self, manifest, results, require_all_pass=True):
        experiment = self.module.read_json(manifest)
        candidate = experiment["conditions"]["revised"]
        snapshot = self.module.contained_file(manifest.parent, candidate["rules_file"])
        self.assertEqual((ROOT / "skills/concise/SKILL.md").read_text(encoding="utf8"),
                         snapshot.read_text(encoding="utf8"), "Collect and review the changed rules again")
        scores = self.module.score_experiment(manifest)
        self.assertEqual(self.module.read_json(results), scores)
        revised = scores["conditions"]["revised"]
        if require_all_pass:
            self.assertEqual(revised["sample_count"], revised["quality_passes"])
        self.assertFalse(revised["unreviewed"])
        return scores
