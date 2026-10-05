"""Score captured response samples offline; keyword checks are not semantic grades."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


REVIEW_FIELDS = ("accurate", "complete", "readable", "unnecessary_question")


def text_hash(text):
    """Hash UTF-8 text with LF newlines, independent of checkout line endings."""
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf8")).hexdigest()


def score_answer(case, sample):
    text = sample.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("A sample must contain nonempty text")
    indicators = {check["label"]: bool(re.search(check["pattern"], text, re.I))
                  for check in case.get("checks", [])}
    review = sample.get("review")
    quality = None
    if review is not None:
        if not isinstance(review, dict) or any(type(review.get(key)) is not bool for key in REVIEW_FIELDS):
            raise ValueError("Review decisions must be actual booleans")
        if not isinstance(review.get("evidence"), str) or not review["evidence"].strip():
            raise ValueError("A semantic review needs evidence")
        if "text_sha256" in review and review["text_sha256"] != text_hash(text):
            raise ValueError("Review belongs to a different answer")
        quality = (review["accurate"] and review["complete"] and review["readable"]
                   and not review["unnecessary_question"])
    maximum = case.get("max_characters")
    return {
        "case_id": case["id"], "characters": len(text),
        "lines": len(text.splitlines()),
        "content_indicators": indicators,
        "content_indicators_pass": all(indicators.values()),
        "length_target_pass": None if maximum is None else len(text) <= maximum,
        "quality_pass": quality,
    }


def score_condition(cases, samples):
    case_ids = [case["id"] for case in cases]
    sample_ids = [sample.get("case_id") for sample in samples]
    if not case_ids or len(set(case_ids)) != len(case_ids):
        raise ValueError("Cases need unique IDs and cannot be empty")
    if len(sample_ids) != len(set(sample_ids)) or set(sample_ids) != set(case_ids):
        raise ValueError("Samples must cover every case exactly once")
    by_id = {sample["case_id"]: sample for sample in samples}
    answers = [score_answer(case, by_id[case["id"]]) for case in cases]
    return {
        "answers": answers, "sample_count": len(answers),
        "characters": sum(answer["characters"] for answer in answers),
        "content_indicator_passes": sum(answer["content_indicators_pass"] for answer in answers),
        "reviewed": sum(answer["quality_pass"] is not None for answer in answers),
        "quality_passes": sum(answer["quality_pass"] is True for answer in answers),
        "quality_failures": [answer["case_id"] for answer in answers if answer["quality_pass"] is False],
        "unreviewed": [answer["case_id"] for answer in answers if answer["quality_pass"] is None],
    }


def read_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def contained_file(root, name):
    if not isinstance(name, str) or Path(name).is_absolute():
        raise ValueError("Experiment paths must be relative")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Missing or out-of-root experiment file: {name}")
    return path


def experiment_fingerprint(experiment):
    """Bind review-time scenarios and rule versions, including the no-rules arm."""
    sources = {"cases_sha256": experiment["cases_sha256"],
               "rules_sha256": {mode: condition.get("rules_sha256")
                                for mode, condition in experiment["conditions"].items()}}
    return text_hash(json.dumps(sources, sort_keys=True, separators=(",", ":")))


def score_experiment(path):
    experiment = read_json(path)
    root = path.parent
    cases_path = contained_file(root, experiment["cases_file"])
    if text_hash(cases_path.read_text(encoding="utf8")) != experiment["cases_sha256"]:
        raise ValueError("Scenario suite changed since collection")
    cases = read_json(cases_path)
    results = {}
    for mode, condition in experiment["conditions"].items():
        rules = condition.get("rules_file")
        if rules is not None:
            rules_path = contained_file(root, rules)
            if text_hash(rules_path.read_text(encoding="utf8")) != condition["rules_sha256"]:
                raise ValueError(f"Rules changed since collection: {mode}")
        elif condition.get("rules_sha256") is not None:
            raise ValueError("A no-rules condition cannot have a rules hash")
        samples = read_json(contained_file(root, condition["answers_file"]))
        reviews_path = condition.get("reviews_file")
        if reviews_path is not None:
            document = read_json(contained_file(root, reviews_path))
            if not isinstance(document.get("reviewer"), str) or not document["reviewer"].strip():
                raise ValueError("Review provenance is required")
            if document.get("source_fingerprint") != experiment_fingerprint(experiment):
                raise ValueError("Review source fingerprint differs from this experiment")
            reviews = document["conditions"][mode]
            review_ids = [review["case_id"] for review in reviews]
            if len(review_ids) != len(set(review_ids)) or set(review_ids) != {sample["case_id"] for sample in samples}:
                raise ValueError("Reviews must cover every sample exactly once")
            by_id = {review["case_id"]: review for review in reviews}
            for sample in samples:
                review = by_id[sample["case_id"]]
                if "text_sha256" not in review:
                    raise ValueError("Persisted reviews need an answer hash")
                sample["review"] = review
        elif any("review" in sample for sample in samples):
            raise ValueError("Use a separate review file with provenance")
        results[mode] = score_condition(cases, samples)
    if not results:
        raise ValueError("An experiment needs at least one condition")
    return {"collection": experiment["collection"], "conditions": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path, help="Experiment manifest JSON")
    parser.add_argument("--output", type=Path, help="Write the scored report as JSON")
    parser.add_argument("--require-quality", action="store_true", help="Fail on unreviewed or failed semantic grades")
    parser.add_argument("--condition", action="append", help="Apply the quality gate only to these condition names")
    args = parser.parse_args()
    try:
        report = score_experiment(args.experiment.resolve())
        if args.condition and set(args.condition) - report["conditions"].keys():
            raise ValueError("Unknown quality-gate condition")
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Invalid evaluation: {error}", file=sys.stderr)
        return 2
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf8")
    for mode, result in report["conditions"].items():
        print(f"{mode}: quality {result['quality_passes']}/{result['sample_count']}; "
              f"reviewed {result['reviewed']}; indicators {result['content_indicator_passes']}; "
              f"characters {result['characters']}")
    selected = args.condition or list(report["conditions"])
    if args.require_quality and any(report["conditions"][mode]["unreviewed"] or report["conditions"][mode]["quality_failures"] for mode in selected):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
