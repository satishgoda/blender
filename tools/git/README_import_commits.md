Recreate commits from a source Git repo into a target repo (file-only import)

Overview
--------
This set of helper scripts allows you to replay commits from a source Git repository into another repository by recreating commits and applying only the exact file changes touched in the specified commit range.

Why Option B
------------
- Preserves exact file contents and the chronological order of commits.
- Avoids bringing any unrelated files from the source repository into the target repo.
- Allows preserving original authorship, timestamps, and commit messages.

Important notes
---------------
- These scripts require `git` on PATH.
- They operate on repo paths you provide — they can and will modify the target repo unless you use the `--dry-run` flag.
- If the target repo contains conflicting files in target paths, you may need to resolve conflicts yourself.

Scripts
-------
- `tools/git/extract_commit_range.py`: Extract commit metadata and a file list for each commit in the range (read-only).
- `tools/git/recreate_commits_from_range.py`: The main script to replay commits into a target repo by applying only the touched files and committing them.

Usage: Extraction (read-only)
-----------------------------
1) Generate a JSON summary of the commit range, including the files touched per commit:

```bash
python3 tools/git/extract_commit_range.py /path/to/source/repo 4a1d88d0213dc49c2f036affbf989552cf6daf6d 5357339fb4ff1ef3df6cb5129541ef00e408cf14 --json-out /tmp/blender_commit_range.json
```

This produces `/tmp/blender_commit_range.json` which contains the commits, fileSummary, and any notes.

Usage: Recreate commits into target (Option B)
----------------------------------------------
1) Prepare your target repo (or clone it):

```bash
# If not already cloned
git clone https://github.com/satishgoda/blender-study /tmp/blender-study
cd /tmp/blender-study

# Checkout the branch you want to import into (the script will create a new branch if required)
```

2) Run the replay script in dry-run mode to preview actions:

```bash
python3 tools/git/recreate_commits_from_range.py \
  --src /Users/sgoda/dev/b3d/blender \
  --start 4a1d88d0213dc49c2f036affbf989552cf6daf6d \
  --end 5357339fb4ff1ef3df6cb5129541ef00e408cf14 \
  --dest /tmp/blender-study --dry-run
```

3) If the output looks as expected, run without `--dry-run`:

```bash
python3 tools/git/recreate_commits_from_range.py \
  --src /Users/sgoda/dev/b3d/blender \
  --start 4a1d88d0213dc49c2f036affbf989552cf6daf6d \
  --end 5357339fb4ff1ef3df6cb5129541ef00e408cf14 \
  --dest /tmp/blender-study --preserve-author
```

4) Validate commit count, commit messages, and file contents in the target repo:

```bash
cd /tmp/blender-study
# Show the last imported commits
git log --oneline --decorate --graph
# Show a commit's files
git show --name-status <commit-sha>
# Compare file contents between the source commit and the new commit
# Optionally use git diff or check checksums.
```

Branching & Safety
------------------
- The script will create a new branch by default named `import/<start>-<end>-<timestamp>` unless `--branch` is provided.
- Ensure you run the script on a clean working copy in the target repo (no staged files) for best results.

Next steps and PR
------------------
- After verifying the import in the target repo, push and open a PR for code review:

```bash
# push
git push origin your-import-branch
# open PR in the usual GitHub workflow
```

Potential enhancements
----------------------
- Add more robust commit mapping to prevent accidental duplication when re-replaying commits.
- Report a diff summary between source commit and replayed commit for validation.
- More robust handling for large binary files using `git cat-file` directly.

If you want, I can run the extraction step in this workspace to provide the commit list and file summary (read-only). Or I can prepare and run the replay script locally if you grant permission to modify the target repo path. Please let me know next.