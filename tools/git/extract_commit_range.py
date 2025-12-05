#!/usr/bin/env python3
"""
Extract commit metadata and changed files between two commits (inclusive).
Usage:
  python3 extract_commit_range.py /path/to/repo START_SHA END_SHA [--json-out path]
Outputs JSON to stdout or to file with a structure similar to:
{
  "commits": [ {hash, author, email, date, message, files: [{path, change_type, from?}] } ... ],
  "fileSummary": { path -> [list of commits] },
  "notes": [...]
}
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple


def run_git(repo: str, args: List[str]) -> Tuple[int, str, str]:
    cmd = ["git", "-C", repo] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_bytes, err_bytes = p.communicate()
    out = out_bytes.decode("utf-8", errors="replace")
    err = err_bytes.decode("utf-8", errors="replace")
    return p.returncode, out, err


def verify_commit(repo: str, sha: str) -> bool:
    rc, out, err = run_git(repo, ["rev-parse", "--verify", sha])
    return rc == 0


def commits_in_range(repo: str, start: str, end: str) -> List[str]:
    rc, out, err = run_git(repo, ["rev-list", "--reverse", f"{start}^..{end}"])
    if rc != 0:
        # fallback: try start..end (may exclude start)
        rc2, out2, err2 = run_git(repo, ["rev-list", "--reverse", f"{start}..{end}"])
        if rc2 != 0:
            raise RuntimeError(f"git rev-list failed: {err.strip()}")
        commits = out2.strip().splitlines()
        if commits and commits[0] == start:
            return commits
        rc3, out3, err3 = run_git(repo, ["merge-base", "--is-ancestor", start, end])
        if rc3 == 0:
            return [start] + commits
        else:
            return [start] + commits
    else:
        return out.strip().splitlines()


def commit_metadata(repo: str, sha: str) -> Dict[str, Any]:
    rc, out, err = run_git(repo, ["show", "-s", "--format=%H%x1f%an%x1f%ae%x1f%ai%x1f%cn%x1f%ce%x1f%ci%x1f%B", sha])
    if rc != 0:
        raise RuntimeError(f"git show failed for {sha}: {err}")
    parts = out.split("\x1f", 7)
    if len(parts) < 8:
        raise RuntimeError(f"unexpected git show output: {out!r}")
    h, an, ae, ad, cn, ce, cd, body = parts
    body = body.rstrip('\n')
    rc, files_out, err = run_git(repo, ["diff-tree", "--no-commit-id", "-r", "--name-status", sha])
    if rc != 0:
        raise RuntimeError(f"git diff-tree failed for {sha}: {err}")
    files = []
    for line in files_out.strip().splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") or status.startswith("C"):
            if len(parts) >= 3:
                old, new = parts[1], parts[2]
                files.append({"path": new, "change_type": status, "from": old})
            else:
                files.append({"path": parts[-1], "change_type": status})
        else:
            files.append({"path": parts[-1], "change_type": status})
    rc, outp, err = run_git(repo, ["rev-list", "--parents", "-n", "1", sha])
    parents = outp.strip().split()
    is_merge = len(parents) > 2
    msg_first_line = body.strip().splitlines()[0] if body else ""
    return {
        "hash": h.strip(),
        "author_name": an.strip(),
        "author_email": ae.strip(),
        "author_date": ad.strip(),
        "committer_name": cn.strip(),
        "committer_email": ce.strip(),
        "committer_date": cd.strip(),
        "message": msg_first_line,
        "body": body,
        "files": files,
        "isMerge": is_merge,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="Path to source repo")
    parser.add_argument("start_sha", help="Start commit (inclusive)")
    parser.add_argument("end_sha", help="End commit (inclusive)")
    parser.add_argument("--json-out", default=None, help="Optional path to write JSON output")
    args = parser.parse_args()

    repo = args.repo
    start = args.start_sha
    end = args.end_sha

    if not os.path.isdir(repo):
        print(f"Path not found: {repo}", file=sys.stderr)
        sys.exit(3)
    if not verify_commit(repo, start):
        print(f"Start commit not found: {start}", file=sys.stderr)
        sys.exit(4)
    if not verify_commit(repo, end):
        print(f"End commit not found: {end}", file=sys.stderr)
        sys.exit(5)

    notes: List[str] = []
    commits: List[Dict[str, Any]] = []
    file_summary: Dict[str, List[str]] = {}

    try:
        sha_list = commits_in_range(repo, start, end)
    except Exception as e:
        print(f"Error generating commit list: {e}", file=sys.stderr)
        sys.exit(6)

    if start not in sha_list:
        notes.append(f"Start commit {start} was not included by default; including explicitly.")
        sha_list = [start] + sha_list

    for sha in sha_list:
        md = commit_metadata(repo, sha)
        commits.append(md)
        for f in md['files']:
            path = f['path']
            file_summary.setdefault(path, []).append(md['hash'])

    out = {"commits": commits, "fileSummary": file_summary, "notes": notes}
    if args.json_out:
        with open(args.json_out, 'w') as f:
            json.dump(out, f, indent=2)
        print(f"Wrote JSON to {args.json_out}")
    else:
        print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
