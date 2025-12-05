#!/usr/bin/env python3
"""
Recreate commit range from a source repo into a target repo by replaying only the touched files.

Usage:
  python3 recreate_commits_from_range.py \
    --src /path/to/source/repo --start START_SHA --end END_SHA \
    --dest /path/to/dest/repo [--branch import/blender-commits] [--prefix subdir] [--preserve-author] [--dry-run]

Key behaviors:
- Uses commit list from source repo between START..END (inclusive), in chronological order.
- For each commit, apply changes for the files touched only in the target repo.
- Preserve author and committer metadata if requested (default: yes).
- Performs operations on a new branch in the target repo (default: import/<start>-<end>-<timestamp>)
- Dry-run mode will only print actions without changing the target repo.

Notes:
- This script expects `git` to be on PATH and both repos to be proper git repositories.
- Handles add/modify/delete/rename operations. Copy operations (C) will be treated like add.
- For binary files, content is transferred as-is using `git show` to extract blobs.
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple


def run_cmd(cmd: List[str], capture_output: bool = True, check: bool = False, env=None, cwd: str | None = None) -> Tuple[int, str, str]:
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE if capture_output else None, stderr=subprocess.PIPE if capture_output else None, env=env, cwd=cwd)
    out_bytes, err_bytes = p.communicate()
    out = out_bytes.decode('utf-8', errors='replace') if out_bytes is not None else ''
    err = err_bytes.decode('utf-8', errors='replace') if err_bytes is not None else ''
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed (exit {p.returncode}): {' '.join(cmd)}\nstdout: {out}\nstderr: {err}")
    return p.returncode, out, err


# Uses the helper extract script or replicate logic.
# We'll import logic directly for reliability.


def get_commit_list(src_path: str, start: str, end: str) -> List[str]:
    rc, out, err = run_cmd(["git", "-C", src_path, "rev-list", "--reverse", f"{start}^..{end}"])
    if rc != 0:
        rc2, out2, err2 = run_cmd(["git", "-C", src_path, "rev-list", "--reverse", f"{start}..{end}"])
        if rc2 != 0:
            raise RuntimeError(f"git rev-list failed: {err.strip()} {err2.strip()}")
        commits = out2.strip().splitlines()
        if commits and commits[0] == start:
            return commits
        rc3, out3, err3 = run_cmd(["git", "-C", src_path, "merge-base", "--is-ancestor", start, end])
        if rc3 == 0:
            return [start] + commits
        else:
            return [start] + commits
    else:
        return out.strip().splitlines()


def get_commit_metadata(src_path: str, sha: str) -> Dict[str, Any]:
    rc, out, err = run_cmd(["git", "-C", src_path, "show", "-s", "--format=%H%x1f%an%x1f%ae%x1f%ai%x1f%cn%x1f%ce%x1f%ci%x1f%B", sha])
    if rc != 0:
        raise RuntimeError(f"git show failed for {sha}: {err}")
    parts = out.split('\x1f', 7)
    if len(parts) < 8:
        raise RuntimeError(f"Unexpected git show output: {out!r}")
    h, an, ae, ad, cn, ce, cd, body = parts
    rc, files_out, err = run_cmd(["git", "-C", src_path, "diff-tree", "--no-commit-id", "-r", "--name-status", sha])
    if rc != 0:
        raise RuntimeError(f"git diff-tree failed for {sha}: {err}")
    files = []
    for line in files_out.strip().splitlines():
        if not line:
            continue
        parts = line.split('\t')
        status = parts[0]
        if status.startswith('R') or status.startswith('C'):
            if len(parts) >= 3:
                old, new = parts[1], parts[2]
                files.append({'path': new, 'change_type': status, 'from': old})
            else:
                files.append({'path': parts[-1], 'change_type': status})
        else:
            files.append({'path': parts[-1], 'change_type': status})
    rc, outp, err = run_cmd(["git", "-C", src_path, "rev-list", "--parents", "-n", "1", sha])
    parents = outp.strip().split()
    is_merge = len(parents) > 2
    return {
        'hash': h.strip(),
        'author_name': an.strip(),
        'author_email': ae.strip(),
        'author_date': ad.strip(),
        'committer_name': cn.strip(),
        'committer_email': ce.strip(),
        'committer_date': cd.strip(),
        'message': body.strip(),
        'files': files,
        'is_merge': is_merge,
    }


def extract_blob_to_file(src_path: str, commit_sha: str, filepath: str, target_path: str) -> None:
    # Uses `git show <commit>:<path>` to capture file bytes and write binary to disk
    cmd = ["git", "-C", src_path, "show", f"{commit_sha}:{filepath}"]
    rc, out, err = run_cmd(cmd, capture_output=True)
    if rc != 0:
        raise RuntimeError(f"git show failed for {commit_sha}:{filepath} - {err}")
    # Write as bytes using utf-8 decoding fallback (we use binary via encoding from out)
    # Convert to bytes preserving content: get bytes via subprocess directly to avoid decode/encode issues
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_bytes, err_bytes = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(f"git show failed for {commit_sha}:{filepath} - {err_bytes.decode('utf-8', errors='replace')}")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, 'wb') as f:
        f.write(out_bytes)


def safe_git_add(target_repo: str, files: List[str], dry_run: bool):
    for f in files:
        if dry_run:
            print(f"[DRY] git add {f}")
        else:
            run_cmd(["git", "-C", target_repo, "add", "-f", f], check=True)


def safe_git_rm(target_repo: str, files: List[str], dry_run: bool):
    for f in files:
        if dry_run:
            print(f"[DRY] git rm {f}")
        else:
            # Use --ignore-unmatch to avoid error if file doesn't exist
            run_cmd(["git", "-C", target_repo, "rm", "-f", "--ignore-unmatch", f], check=True)


def safe_git_mv(target_repo: str, old: str, new: str, dry_run: bool):
    if dry_run:
        print(f"[DRY] git mv {old} {new}")
    else:
        run_cmd(["git", "-C", target_repo, "mv", "-f", old, new], check=True)


def ensure_branch(target_repo: str, branch_name: str, dry_run: bool):
    # Create new branch from current HEAD or create it if missing
    if dry_run:
        print(f"[DRY] git checkout -b {branch_name}")
        return
    rc, out, err = run_cmd(["git", "-C", target_repo, "rev-parse", "--verify", branch_name])
    if rc == 0:
        run_cmd(["git", "-C", target_repo, "checkout", branch_name], check=True)
    else:
        run_cmd(["git", "-C", target_repo, "checkout", "-b", branch_name], check=True)


def commit_in_target(target_repo: str, commit_msg: str, author_name: str, author_email: str, author_date: str, committer_name: str, committer_email: str, committer_date: str, dry_run: bool):
    env = os.environ.copy()
    if author_name:
        env['GIT_AUTHOR_NAME'] = author_name
    if author_email:
        env['GIT_AUTHOR_EMAIL'] = author_email
    if author_date:
        env['GIT_AUTHOR_DATE'] = author_date
    if committer_name:
        env['GIT_COMMITTER_NAME'] = committer_name
    if committer_email:
        env['GIT_COMMITTER_EMAIL'] = committer_email
    if committer_date:
        env['GIT_COMMITTER_DATE'] = committer_date
    if dry_run:
        print(f"[DRY] git commit -m <<MSG>> by {author_name} <{author_email}> on {author_date}")
        return None
    # Use -F with a temporary file for multi-line commit message
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        tmp.write(commit_msg)
        tmp.flush()
        tmp_name = tmp.name
    try:
        run_cmd(["git", "-C", target_repo, "commit", "-F", tmp_name, "--no-verify", "--allow-empty"], check=True, env=env)
        rc, sha, err = run_cmd(["git", "-C", target_repo, "rev-parse", "HEAD"], check=True)
        return sha.strip()
    finally:
        os.unlink(tmp_name)


def run_replay(src_repo: str, start_sha: str, end_sha: str, target_repo: str, branch: str | None, prefix: str | None, preserve_authors: bool, dry_run: bool):
    # Validate the repos
    for path in [src_repo, target_repo]:
        if not os.path.isdir(path):
            raise RuntimeError(f"Path not found: {path}")
        rc, out, err = run_cmd(["git", "-C", path, "rev-parse", "--is-inside-work-tree"]) 
        if rc != 0:
            raise RuntimeError(f"Not a Git repo: {path} {err}")

    if not preserve_authors:
        # use current user as author/committer
        rc, out, err = run_cmd(["git", "-C", target_repo, "config", "user.name"]) 
        default_an = out.strip() if rc == 0 else None
        rc, out, err = run_cmd(["git", "-C", target_repo, "config", "user.email"]) 
        default_ae = out.strip() if rc == 0 else None
    else:
        default_an = default_ae = None

    commits = get_commit_list(src_repo, start_sha, end_sha)
    if not commits:
        raise RuntimeError("No commits found in range")

    # Branch name default
    if branch is None:
        branch = f"import/{start_sha[:7]}-{end_sha[:7]}-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    ensure_branch(target_repo, branch, dry_run)

    mapped_commits: Dict[str, str] = {}

    for sha in commits:
        metadata = get_commit_metadata(src_repo, sha)
        touched = metadata['files']
        files_to_add: List[str] = []
        files_to_rm: List[str] = []
        mv_ops: List[Tuple[str, str]] = []

        for f in touched:
            path = f['path']
            status = f['change_type']
            old_path = f.get('from')
            target_path = os.path.join(prefix, path) if prefix else path
            if status == 'D':
                files_to_rm.append(target_path)
            elif status.startswith('R'):
                # rename: from old_path to target_path
                if old_path:
                    old_target = os.path.join(prefix, old_path) if prefix else old_path
                    mv_ops.append((old_target, target_path))
                # also make sure new file content exists, extract it
                extract_blob_to_file(src_repo, sha, path, os.path.join(target_repo, target_path))
                files_to_add.append(target_path)
            elif status == 'A' or status == 'M' or status.startswith('C'):
                # write the file to target repo
                extract_blob_to_file(src_repo, sha, path, os.path.join(target_repo, target_path))
                files_to_add.append(target_path)
            else:
                # Unknown status: add as text content
                extract_blob_to_file(src_repo, sha, path, os.path.join(target_repo, target_path))
                files_to_add.append(target_path)

        # perform moves
        for old, new in mv_ops:
            # If old exists in target, perform git mv to preserve rename; otherwise, just write new and rm old if exists
            if dry_run:
                print(f"[DRY] git mv {old} -> {new}")
            else:
                rc, out, err = run_cmd(["git", "-C", target_repo, "ls-files", "--error-unmatch", old])
                if rc == 0:
                    run_cmd(["git", "-C", target_repo, "mv", "-f", old, new], check=True)
                else:
                    # old not present; skip move but ensure new exists
                    pass

        # perform rm
        safe_git_rm(target_repo, files_to_rm, dry_run)
        # perform add
        safe_git_add(target_repo, files_to_add, dry_run)

        # commit message & author handling
        author_name = metadata['author_name'] if preserve_authors else default_an
        author_email = metadata['author_email'] if preserve_authors else default_ae
        author_date = metadata['author_date'] if preserve_authors else None
        committer_name = metadata['committer_name'] if preserve_authors else default_an
        committer_email = metadata['committer_email'] if preserve_authors else default_ae
        committer_date = metadata['committer_date'] if preserve_authors else None

        if not touched:
            print(f"Skipping empty commit {sha} (no touched files)")
            continue

        # Compose commit message such that the "subject" (first line) matches the original commit's subject.
        full_msg = metadata.get('message', '') or ''
        subject = full_msg.splitlines()[0] if full_msg.strip() else ''
        body = "\n".join(full_msg.splitlines()[1:]).strip()
        commit_msg_lines = []
        if subject:
            commit_msg_lines.append(subject)
        if body:
            commit_msg_lines.append('\n' + body)
        # Include a reference back to the original commit in the commit body (not the subject)
        commit_msg_lines.append('\nOriginal-Commit: ' + sha)
        commit_msg = '\n'.join(commit_msg_lines).strip() + '\n'
        new_sha = commit_in_target(target_repo, commit_msg, author_name, author_email, author_date, committer_name, committer_email, committer_date, dry_run)
        if new_sha is not None:
            mapped_commits[sha] = new_sha.strip()
        print(f"Replayed {sha} -> {mapped_commits.get(sha)}")

    # finished
    print("Replay complete. Mapped commits:")
    print(json.dumps(mapped_commits, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', required=True, help='Path to source repo')
    parser.add_argument('--start', required=True, help='Start commit (inclusive)')
    parser.add_argument('--end', required=True, help='End commit (inclusive)')
    parser.add_argument('--dest', required=True, help='Path to destination repo')
    parser.add_argument('--branch', default=None, help='Target branch name (optional)')
    parser.add_argument('--prefix', default=None, help='Prefix to apply to file paths in target repo')
    parser.add_argument('--no-preserve-author', dest='preserve_authors', action='store_false', help='Do not preserve author/committer details')
    parser.set_defaults(preserve_authors=True)
    parser.add_argument('--dry-run', action='store_true', default=False, help='Show what would happen without making changes')

    args = parser.parse_args()
    run_replay(args.src, args.start, args.end, args.dest, args.branch, args.prefix, args.preserve_authors, args.dry_run)


if __name__ == '__main__':
    main()
