#!/usr/bin/env python3
"""
Validate that a replayed import matches the source commit-by-commit.

Usage:
  python3 tools/git/validate_replay.py --src /path/to/source/repo --branch importBranch --dest /path/to/dest/repo --start START_SHA --end END_SHA --out /tmp/validate_report.json

Behavior:
- For every commit in source range, find the corresponding commit on the destination branch by searching the message for 'Original-Commit: <sha>'.
- For each file changed in the source commit, compare file content at the source commit and at the replayed commit. Report equality, mismatch, missing file, or deleted state.
- Output JSON summary describing commit mapping and per-file status.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple


def run_cmd(cmd: List[str], cwd: str | None = None) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    out, err = p.communicate()
    outt = out.decode('utf-8', errors='replace') if out else ''
    errt = err.decode('utf-8', errors='replace') if err else ''
    return p.returncode, outt, errt


def compute_sha_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def get_blob_bytes(repo: str, commit: str, path: str) -> bytes | None:
    rc, out, err = run_cmd(["git", "-C", repo, "show", f"{commit}:{path}"])
    if rc != 0:
        return None
    # decode as binary via subprocess
    p = subprocess.Popen(["git", "-C", repo, "show", f"{commit}:{path}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    outb, errb = p.communicate()
    if p.returncode != 0:
        return None
    return outb


def find_target_commit_for_source(dest_repo: str, branch: str, src_sha: str) -> str | None:
    rc, out, err = run_cmd(["git", "-C", dest_repo, "log", branch, "--grep", f"Original-Commit: {src_sha}", "--format=%H", "-n", "1"])
    if rc != 0 or not out.strip():
        return None
    return out.strip().splitlines()[0]


def extract_source_changed_files(src_repo: str, src_sha: str) -> List[Dict[str, Any]]:
    # Use diff-tree to list changed files for the commit
    rc, out, err = run_cmd(["git", "-C", src_repo, "diff-tree", "--no-commit-id", "-r", "--name-status", src_sha])
    if rc != 0:
        raise RuntimeError(f"git diff-tree failed for {src_sha}: {err}")
    files = []
    for line in out.strip().splitlines():
        parts = line.split('\t')
        status = parts[0]
        if status.startswith('R') or status.startswith('C'):
            if len(parts) >= 3:
                files.append({'path': parts[2], 'change_type': status, 'from': parts[1]})
            else:
                files.append({'path': parts[-1], 'change_type': status})
        else:
            files.append({'path': parts[-1], 'change_type': status})
    return files


def validate_range(src_repo: str, dest_repo: str, branch: str, start: str, end: str) -> Dict[str, Any]:
    # Build commits list from the src range
    rc, out, err = run_cmd(["git", "-C", src_repo, "rev-list", "--reverse", f"{start}^..{end}"])
    if rc != 0:
        rc2, out2, err2 = run_cmd(["git", "-C", src_repo, "rev-list", "--reverse", f"{start}..{end}"])
        if rc2 != 0:
            raise RuntimeError(f"git rev-list failed: {err.strip()}")
        commits = out2.strip().splitlines()
        if commits and commits[0] == start:
            pass
        else:
            commits = [start] + commits
    else:
        commits = out.strip().splitlines()
    report: Dict[str, Any] = {'range': {'start': start, 'end': end}, 'commits': []}
    for sha in commits:
        entry = {'src_sha': sha}
        entry['src_meta'] = {}
        # get mapping commit in dest
        target_sha = find_target_commit_for_source(dest_repo, branch, sha)
        entry['target_sha'] = target_sha
        files = extract_source_changed_files(src_repo, sha)
        entry['files'] = []
        for f in files:
            src_path = f['path']
            status = f['change_type']
            # Get bytes from src commit
            src_bytes = get_blob_bytes(src_repo, sha, src_path)
            if target_sha:
                # get similarly from target commit; note that the target commit path might be different (if prefix applied)
                target_bytes = get_blob_bytes(dest_repo, target_sha, src_path)
            else:
                target_bytes = None
            if status == 'D':
                # If removed, ensure target also does not have file
                file_status = 'Deleted in src'
                if target_bytes is None:
                    file_status = 'OK: Deleted in target'
                else:
                    file_status = 'Mismatch: exists in target but deleted in src'
            else:
                if src_bytes is None and status != 'D':
                    file_status = 'Error: missing in src commit'
                else:
                    if target_bytes is None:
                        file_status = 'Missing in target'
                    else:
                        if compute_sha_bytes(src_bytes) == compute_sha_bytes(target_bytes):
                            file_status = 'Match'
                        else:
                            file_status = 'Mismatch'
            entry['files'].append({'path': src_path, 'status': file_status})
        report['commits'].append(entry)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True)
    parser.add_argument('--dest', required=True)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--out', default='/tmp/validate_replay.json')
    args = parser.parse_args()
    report = validate_range(args.src, args.dest, args.branch, args.start, args.end)
    with open(args.out, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Wrote validation report to {args.out}")


if __name__ == '__main__':
    main()
