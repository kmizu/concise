#!/usr/bin/env python3
"""Capture answers from Claude Code for the response evaluation suite.

Each case runs in a fresh `claude -p` session with user settings disabled and
no tools. A condition is either no concise rules, or a plugin directory whose
SessionStart hook injects a frozen ruleset (the real always-on path). Answers
are written unedited as a JSON array of {case_id, text}.

    python scripts/collect_claude_answers.py evals/prompts.json out.json
    python scripts/collect_claude_answers.py evals/prompts.json out.json --plugin-dir /path/to/concise@0.4.0

The scenarios are fictional text-only vignettes; no scenario action is executed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def build_message(case: dict) -> str:
    context = (case.get("context") or "").strip()
    prompt = case["prompt"].strip()
    if not context:
        return prompt
    return f"Context: {context}\n\n{prompt}"


def run_case(claude: str, case: dict, plugin_dir: str | None, model: str | None, cwd: Path) -> dict:
    command = [claude, "-p", "--setting-sources", "", "--tools", ""]
    if plugin_dir:
        command += ["--plugin-dir", plugin_dir]
    if model:
        command += ["--model", model]
    result = subprocess.run(
        command,
        input=build_message(case),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{case['id']}: claude exited {result.returncode}: {result.stderr.strip()[:300]}")
    text = result.stdout.replace("\r\n", "\n").strip()
    if not text:
        raise RuntimeError(f"{case['id']}: empty answer")
    return {"case_id": case["id"], "text": text}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("prompts", help="prompt-only cases JSON (evals/prompts.json)")
    parser.add_argument("output", help="answers JSON to write")
    parser.add_argument("--plugin-dir", help="plugin directory whose hook injects the rules; omit for no rules")
    parser.add_argument("--model", help="model override passed to claude -p")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    claude = shutil.which("claude")
    if not claude:
        print("claude is not on PATH", file=sys.stderr)
        return 2
    cases = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    plugin_dir = str(Path(args.plugin_dir).resolve()) if args.plugin_dir else None

    # Run from an empty directory that is not a git repository. Claude Code adds
    # the working directory's git status and project files to its context, which
    # would leak real repository state into answers about fictional scenarios.
    with tempfile.TemporaryDirectory(prefix="concise-eval-") as scratch, ThreadPoolExecutor(max_workers=args.workers) as pool:
        cwd = Path(scratch)
        answers = list(pool.map(lambda c: run_case(claude, c, plugin_dir, args.model, cwd), cases))

    Path(args.output).write_text(json.dumps(answers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(answers)} answers to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
