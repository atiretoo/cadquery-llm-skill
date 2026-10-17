#!/usr/bin/env python3
"""
Autonomous CadQuery LLM Skill updater.
Compares upstream CadQuery documentation changes (doc/*.rst), syncs the local
docs/ snapshot, and uses the Google Gemini API to synthesize relevant updates
into SKILL.md, concepts/*.md, and patterns/*.md while preserving critical rules.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SKILL_FILES = [
    "SKILL.md",
    "concepts/brep-mindset.md",
    "concepts/workplanes.md",
    "concepts/selectors.md",
    "concepts/free-function-api.md",
    "patterns/common-patterns.md",
    "patterns/anti-patterns.md",
]

REQUIRED_PHRASES = {
    "SKILL.md": [
        "name: cadquery",
        "description:",
        "# CadQuery LLM Skill",
        "## Two APIs",
        "## The Core Mindset: BRep, Not CSG",
        "## Workplanes",
        "## Selectors",
        "## Critical Anti-Patterns",
        '"ZX"',
        '"XZ"',
    ],
    "concepts/workplanes.md": [
        "# Workplanes",
        '### Named Plane Orientation (`"ZX"` vs `"XZ"`)',
        '"ZX"',
        '"XZ"',
    ],
    "patterns/anti-patterns.md": [
        "# Anti-Patterns",
        "## 1. The CSG Reflex",
        "## 15. Reverse-Ordered Named Workplanes",
    ],
}


def run_git(cmd: list[str], cwd: str) -> str:
    res = subprocess.run(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
    )
    return res.stdout.strip()


def call_gemini_json(api_key: str, prompt: str, model: str = "gemini-2.5-flash") -> dict:
    models_to_try = [model, "gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = None

    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 16384,
                "responseMimeType": "application/json",
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                if text.startswith("```json"):
                    text = text[len("```json") :].strip()
                elif text.startswith("```"):
                    text = text[len("```") :].strip()
                if text.endswith("```"):
                    text = text[:-3].strip()
                return json.loads(text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            print(f"Warning: Gemini model {m} failed with HTTP {e.code}: {err_body}", file=sys.stderr)
            last_err = e
        except Exception as e:
            print(f"Warning: Gemini model {m} failed with error: {e}", file=sys.stderr)
            last_err = e

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


def set_github_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            if "\n" in value:
                delimiter = "EOF"
                f.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                f.write(f"{name}={value}\n")


def sync_docs_snapshot(cadquery_dir: Path, repo_root: Path, new_commit: str) -> list[str]:
    """Copy updated .rst files from upstream CadQuery doc/ into local docs/."""
    upstream_doc = cadquery_dir / "doc"
    local_docs = repo_root / "docs"
    synced = []

    if not upstream_doc.exists() or not local_docs.exists():
        return synced

    for rst_file in sorted(upstream_doc.glob("*.rst")):
        dest = local_docs / rst_file.name
        if not dest.exists() or dest.read_bytes() != rst_file.read_bytes():
            shutil.copy2(rst_file, dest)
            synced.append(f"docs/{rst_file.name}")

    version_file = local_docs / "VERSION"
    version_file.write_text(f"{new_commit}\n", encoding="utf-8")
    synced.append("docs/VERSION")
    return synced


def validate_updated_file(rel_path: str, content: str) -> None:
    phrases = REQUIRED_PHRASES.get(rel_path, [])
    for phrase in phrases:
        if phrase not in content:
            raise ValueError(
                f"Safety validation failed for {rel_path}: missing required phrase '{phrase}'"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Update cadquery-llm-skill based on upstream CadQuery documentation changes."
    )
    parser.add_argument("--cadquery-dir", required=True, help="Path to upstream CadQuery repository")
    parser.add_argument("--repo-root", default=".", help="Path to cadquery-llm-skill root")
    parser.add_argument(
        "--commit-file", default=".upstream_commit", help="Path to tracked upstream commit file"
    )
    args = parser.parse_args()

    cadquery_dir = Path(args.cadquery_dir).resolve()
    repo_root = Path(args.repo_root).resolve()
    commit_file = (repo_root / args.commit_file).resolve()

    if not commit_file.exists():
        print(f"ERROR: Commit file {commit_file} not found.", file=sys.stderr)
        sys.exit(1)

    old_commit = commit_file.read_text(encoding="utf-8").strip()
    new_commit = run_git(["git", "rev-parse", "HEAD"], cwd=str(cadquery_dir))
    print(f"Tracking CadQuery commits: {old_commit} -> {new_commit}")

    if old_commit == new_commit:
        print("Upstream commit has not changed. Everything is up to date.")
        set_github_output("docs_changed", "false")
        return

    diff_stat = run_git(
        ["git", "diff", "--stat", old_commit, new_commit, "--", "doc/"], cwd=str(cadquery_dir)
    )
    if not diff_stat:
        print("Upstream updated, but NO files under doc/ were modified.")
        commit_file.write_text(new_commit + "\n", encoding="utf-8")
        set_github_output("docs_changed", "false")
        set_github_output("commit_advanced", "true")
        set_github_output("new_commit", new_commit)
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY environment variable is missing but doc changes were detected.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Documentation changes detected in upstream CadQuery:")
    print(diff_stat)

    commit_log = run_git(
        ["git", "log", "--oneline", f"{old_commit}..{new_commit}", "--", "doc/"],
        cwd=str(cadquery_dir),
    )
    diff_content = run_git(
        ["git", "diff", old_commit, new_commit, "--", "doc/"], cwd=str(cadquery_dir)
    )
    if len(diff_content) > 50000:
        diff_content = diff_content[:50000] + "\n\n... [diff truncated due to size] ...\n"

    # Sync local docs/*.rst snapshot
    synced_doc_files = sync_docs_snapshot(cadquery_dir, repo_root, new_commit)

    # Read current skill markdown files
    current_files = {}
    for rel_path in SKILL_FILES:
        full_path = repo_root / rel_path
        if full_path.exists():
            current_files[rel_path] = full_path.read_text(encoding="utf-8")

    files_blob = "\n\n".join(
        f"=== FILE: {rel_path} ===\n{content}" for rel_path, content in current_files.items()
    )

    prompt = f"""You are an autonomous maintainer of the `cadquery-llm-skill` repository.
The official CadQuery documentation (`doc/`) was updated in upstream commits:
{commit_log}

Here is the git diff of the upstream documentation changes:
```diff
{diff_content}
```

Here are the current skill markdown files in `cadquery-llm-skill`:
{files_blob}

TASK:
Determine whether any of the skill markdown files ({", ".join(SKILL_FILES)}) need updates to reflect new methods, changed API signatures, or new idioms introduced in the upstream `doc/` diff.

CRITICAL CONSTRAINTS:
1. PRESERVE YAML FRONTMATTER: `SKILL.md` MUST start with its YAML frontmatter (`name: cadquery` and `description:`).
2. PRESERVE BREP MINDSET & TWO-API STRUCTURE: Maintain the repository's BRep-over-CSG mindset and Fluent vs. Free Function API organization.
3. PRESERVE WORKPLANE CYCLIC ORDER RULES: You MUST preserve the `"ZX"` vs `"XZ"` workplane orientation rules (that `Workplane("XZ")` has normal `-Y`, `Workplane("ZX")` has normal `+Y` with local 2D coordinates `(z, x)`) in `SKILL.md`, `concepts/workplanes.md`, and `patterns/anti-patterns.md`.
4. MINIMAL, TARGETED EDITS: Only include files in `updated_files` that genuinely require changes. If the upstream doc diff is purely cosmetic (typos, formatting, sphinx config) and no skill markdown files need changes, return an empty object `{{}}` for `updated_files`.

OUTPUT JSON SCHEMA:
Return a JSON object with exactly two keys:
- `"summary"`: A concise markdown summary explaining how the upstream doc changes affect (or do not affect) the skill files.
- `"updated_files"`: An object mapping relative file paths (only from {json.dumps(SKILL_FILES)}) to their complete, updated file content string.
"""

    print("Sending prompt to Gemini API...")
    response_data = call_gemini_json(api_key, prompt)

    updated_files = response_data.get("updated_files", {})
    ai_summary = response_data.get("summary", "Automated sync with upstream CadQuery docs.")

    modified_skill_files = []
    for rel_path, new_content in updated_files.items():
        if rel_path not in SKILL_FILES:
            print(f"Skipping unknown file path from model response: {rel_path}", file=sys.stderr)
            continue
        if not isinstance(new_content, str) or not new_content.strip():
            continue
        validate_updated_file(rel_path, new_content)
        target_path = repo_root / rel_path
        target_path.write_text(new_content.rstrip() + "\n", encoding="utf-8")
        modified_skill_files.append(rel_path)

    # Advance .upstream_commit
    commit_file.write_text(new_commit + "\n", encoding="utf-8")

    print(
        f"Synced {len(synced_doc_files)} docs/ files and updated {len(modified_skill_files)} skill files."
    )

    set_github_output("docs_changed", "true")
    set_github_output("old_commit", old_commit[:7])
    set_github_output("new_commit", new_commit[:7])
    set_github_output("pr_title", f"Autonomous Update: CadQuery doc changes ({new_commit[:7]})")

    summary_file = repo_root / "update_summary.md"
    summary_lines = [
        "### Upstream CadQuery Documentation Changes",
        "",
        f"Updated from `{old_commit[:7]}` to `{new_commit[:7]}`.",
        "",
        "#### AI Synthesis Summary",
        ai_summary,
        "",
        "#### Skill Files Modified",
        "\n".join(f"- `{p}`" for p in modified_skill_files) if modified_skill_files else "- None (only `docs/` snapshot updated)",
        "",
        "#### Upstream Commits",
        f"```\n{commit_log}\n```",
        "",
        "#### Upstream `doc/` Diff Stat",
        f"```\n{diff_stat}\n```",
    ]
    summary_file.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
