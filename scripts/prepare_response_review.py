"""Prepare a blinded review, then attach its decisions to hashed answer texts."""

import argparse
import json
import random
from pathlib import Path

from evaluate_responses import contained_file, experiment_fingerprint, read_json, score_answer, score_experiment, text_hash


def serialize_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def prepare(manifest, seed):
    score_experiment(manifest)  # Validate source hashes and complete capture coverage.
    experiment = read_json(manifest)
    root = manifest.parent
    cases = read_json(contained_file(root, experiment["cases_file"]))
    captures = {mode: {sample["case_id"]: sample["text"] for sample in
                      read_json(contained_file(root, condition["answers_file"]))}
                for mode, condition in experiment["conditions"].items()}
    rng = random.Random(seed)
    blind_cases, mapping = [], []
    for case in cases:
        modes = list(captures)
        rng.shuffle(modes)
        answers = {}
        for index, mode in enumerate(modes):
            variant = f"response-{index + 1}"
            text = captures[mode][case["id"]]
            answers[variant] = text
            mapping.append({"case_id": case["id"], "variant": variant, "condition": mode,
                            "text_sha256": text_hash(text)})
        blind_cases.append({key: case[key] for key in ("id", "context", "prompt", "rubric")}
                           | {"answers": answers})
    return {"source_fingerprint": experiment_fingerprint(experiment), "cases": blind_cases}, {
        "seed": seed, "cases_sha256": experiment["cases_sha256"], "mapping": mapping}


def attach(manifest, key, decisions):
    experiment = read_json(manifest)
    expected_input, expected_key = prepare(manifest, key["seed"])  # Validate current source files.
    if key != expected_key:
        raise ValueError("Invalid or stale review mapping")
    if decisions.get("review_input_sha256") != text_hash(serialize_json(expected_input)):
        raise ValueError("Decisions belong to a different reviewed input")
    if not isinstance(decisions.get("reviewer"), str) or not decisions["reviewer"].strip():
        raise ValueError("Independent reviewer provenance is required")
    reviews = decisions["reviews"]
    pairs = [(review["case_id"], review["variant"]) for review in reviews]
    mapping = key["mapping"]
    expected_pairs = {(entry["case_id"], entry["variant"]) for entry in expected_key["mapping"]}
    if len(pairs) != len(set(pairs)) or set(pairs) != expected_pairs:
        raise ValueError("Blind reviews must cover every response exactly once")
    by_pair = dict(zip(pairs, reviews))
    result = {"reviewer": decisions["reviewer"], "source_fingerprint": experiment_fingerprint(experiment),
              "review_input_sha256": decisions["review_input_sha256"],
              "conditions": {mode: [] for mode in experiment["conditions"]}}
    for entry in mapping:
        review = by_pair[(entry["case_id"], entry["variant"])]
        sample_review = {key: value for key, value in review.items() if key != "variant"}
        sample_review["text_sha256"] = entry["text_sha256"]
        # Validate boolean decisions and evidence before persisting them.
        score_answer({"id": entry["case_id"]}, {"text": "validation", "review":
                     {key: value for key, value in sample_review.items() if key != "text_sha256"}})
        result["conditions"][entry["condition"]].append(sample_review)
    return result


def write_json(path, value):
    path.write_text(serialize_json(value), encoding="utf8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--seed", type=int, default=20261006)
    parser.add_argument("--attach", type=Path, help="Independent blinded decisions JSON")
    args = parser.parse_args()
    manifest = args.manifest.resolve()
    root = manifest.parent
    if args.attach:
        write_json(root / "reviews.json", attach(manifest, read_json(root / "review-key.json"), read_json(args.attach)))
        print("Wrote reviews.json; set reviews_file to reviews.json in each manifest condition.")
    else:
        blind, key = prepare(manifest, args.seed)
        write_json(root / "review-input.json", blind)
        write_json(root / "review-key.json", key)
        print("Wrote review-input.json and review-key.json. Show the reviewer only review-input.json.")


if __name__ == "__main__":
    main()
