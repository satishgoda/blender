#!/usr/bin/env python3
"""
Generate a Markdown validation report from the validation JSON file produced by validate_replay.py.

Usage:
  python3 tools/git/generate_markdown_report.py --json /tmp/validate_replay.json --out ~/Desktop/blender_replay_validation_report.md

This script reads /tmp/validate_replay.json and creates a visually appealing Markdown report summarizing validation results.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List


def format_commit_row(idx: int, commit: Dict[str, Any]) -> str:
    src_sha = commit['src_sha']
    target_sha = commit.get('target_sha') or '—'
    files = commit.get('files', [])
    n_files = len(files)
    status_counts = {'Match': 0, 'Mismatch': 0, 'Missing in target': 0, 'OK: Deleted in target': 0}
    for f in files:
        s = f['status']
        if 'Match' in s:
            status_counts['Match'] += 1
        elif 'Mismatch' in s:
            status_counts['Mismatch'] += 1
        elif 'Missing' in s:
            status_counts['Missing in target'] += 1
        elif 'Deleted' in s and 'OK' in s:
            status_counts['OK: Deleted in target'] += 1
        else:
            # Other statuses
            pass
    status_summary = []
    if status_counts['Match']:
        status_summary.append(f"✅ {status_counts['Match']} Match")
    if status_counts['Mismatch']:
        status_summary.append(f"⚠️ {status_counts['Mismatch']} Mismatch")
    if status_counts['Missing in target']:
        status_summary.append(f"❌ {status_counts['Missing in target']} Missing")
    if status_counts['OK: Deleted in target']:
        status_summary.append(f"🗑️ {status_counts['OK: Deleted in target']} Deleted")
    return f"| {idx} | `{src_sha[:7]}` | `{target_sha[:7]}` | {n_files} | {', '.join(status_summary)} |"


def generate_markdown(report: Dict[str, Any]) -> str:
    range_info = report.get('range', {})
    start = range_info.get('start')
    end = range_info.get('end')
    commits = report.get('commits', [])

    total_commits = len(commits)
    total_files = sum(len(c.get('files', [])) for c in commits)
    match = sum(1 for c in commits for f in c.get('files', []) if 'Match' == f['status'])
    mismatch = sum(1 for c in commits for f in c.get('files', []) if 'Mismatch' == f['status'])
    missing = sum(1 for c in commits for f in c.get('files', []) if 'Missing' in f['status'])
    deleted_ok = sum(1 for c in commits for f in c.get('files', []) if 'OK: Deleted' in f['status'])

    lines: List[str] = []
    lines.append("# 🔎 Replay Validation Report — Blender Study Import")
    lines.append("")
    lines.append(f"**Range**: `{start}` → `{end}`")
    lines.append(f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%SZ')} (UTC)")
    lines.append("")
    lines.append("---")

    # Summary
    lines.append("## 📋 Summary")
    lines.append("")
    lines.append(f"- **Total commits verified**: **{total_commits}**")
    lines.append(f"- **Total files considered**: **{total_files}**")
    lines.append("")
    # Quick stats block
    lines.append("### ✅ Validation Statistics")
    lines.append("")
    lines.append(f"- ✅ Matches: **{match}**")
    lines.append(f"- ⚠️ Mismatches: **{mismatch}**")
    lines.append(f"- ❌ Missing in target: **{missing}**")
    lines.append(f"- 🗑️ Deleted and OK in target: **{deleted_ok}**")
    lines.append("")
    lines.append("---")

    # Commit table overview
    lines.append("## 🧾 Commits Overview")
    lines.append("")
    lines.append("| # | Source | Replayed | Files | Status |")
    lines.append("|---|--------|----------|------:|--------:|")
    for i, commit in enumerate(commits, start=1):
        lines.append(format_commit_row(i, commit))
    lines.append("")

    lines.append("---")

    # Per-commit detailed section
    lines.append("## 🔍 Per-Commit Validation Details")
    lines.append("")
    for i, c in enumerate(commits, start=1):
        src_sha = c['src_sha']
        target_sha = c.get('target_sha') or '—'
        lines.append(f"### {i}. `{src_sha}` → `{target_sha}`")
        lines.append("")
        lines.append(f"**Commit metadata**: `Original-Commit: {src_sha}`")
        lines.append("")
        files = c.get('files', [])
        if not files:
            lines.append("No files were touched in this commit.")
            lines.append("")
            continue
        lines.append("**Files changed**:")
        lines.append("")
        lines.append("| Path | Status |")
        lines.append("|------|--------|")
        for f in files:
            p = f['path']
            status = f['status']
            emoji = '✅' if 'Match' in status else ('⚠️' if 'Mismatch' in status else ('❌' if 'Missing' in status else ('🗑️' if 'Deleted' in status else 'ℹ️')))
            lines.append(f"| `{p}` | {emoji} {status} |")
        lines.append("")

    lines.append("---")
    lines.append("## 🛠️ Scripts & Actions Used")
    lines.append("")
    lines.append("- `tools/git/extract_commit_range.py` — Extract metadata and file lists for the specified commit range (read-only).")
    lines.append("- `tools/git/recreate_commits_from_range.py` — Recreate commits into the target repo, applying only touched files per commit.")
    lines.append("- `tools/git/validate_replay.py` — Validate and compare source commit files to replayed commit files.")
    lines.append("")
    lines.append("---")
    lines.append("## ✅ Recommendations & Observations")
    lines.append("")
    if mismatch:
        lines.append("- ⚠️ Some file mismatches were detected. Please review the `Mismatch` entries above and compare diffs manually to identify root causes.")
    else:
        lines.append("- ✅ All compared files match perfectly. No unexpected differences were found.")
    lines.append("")
    lines.append("- If you want me to open a PR with these changes, or change the placement under a subdirectory (prefix), let me know and I’ll handle it.")
    lines.append("")
    lines.append("---")
    lines.append("*End of report* — generated automatically.*")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', required=True, help='Path to validation JSON file')
    parser.add_argument('--out', required=True, help='Path to output Markdown report (e.g., ~/Desktop/..md)')
    args = parser.parse_args()

    with open(args.json, 'r') as f:
        report = json.load(f)
    md = generate_markdown(report)
    out_path = os.path.expanduser(args.out)
    with open(out_path, 'w') as f:
        f.write(md)
    print(f"Wrote Markdown validation report to {out_path}")


if __name__ == '__main__':
    main()
