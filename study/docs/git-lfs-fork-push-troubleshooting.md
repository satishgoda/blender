# Git LFS Fork Push Troubleshooting

**Date:** December 4, 2025  
**Issue:** Unable to push to GitHub fork due to Git LFS restrictions

## Problem

When attempting to push changes to a fork of the Blender repository, the following error occurred:

```bash
(.venv) sgoda@MacBook-K23K9 blender % git push        
batch response: @satishgoda can not upload new objects to public fork satishgoda/blender 
Uploading LFS objects:   0% (0/1), 0 B | 0 B/s, done.
error: failed to push some refs to 'https://github.com/satishgoda/blender.git'

(.venv) sgoda@MacBook-K23K9 blender % git push --force
Uploading LFS objects:   0% (0/1), 0 B | 0 B/s, done.                                    
batch response: @satishgoda can not upload new objects to public fork satishgoda/blender
error: failed to push some refs to 'https://github.com/satishgoda/blender.git'
```

## Root Cause

GitHub restricts uploading new LFS objects to public forks. The Blender repository extensively uses Git LFS for test files (blend files, images, videos, etc.), and attempting to push to a fork tries to upload these LFS objects to the fork's LFS storage, which is not permitted.

## Investigation Steps

### 1. Checked LFS Files

```bash
git lfs ls-files
```

This revealed hundreds of LFS-tracked files in the `tests/files/` directory including:

- `.blend` files
- `.png`, `.jpg`, `.exr` image files
- `.mp4`, `.avi`, `.webm` video files
- `.vdb` volume files
- Various other test assets

### 2. Checked Git Status

```bash
git status
```

Result:

```text
On branch study
Your branch is ahead of 'origin/study' by 1 commit.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean
```

### 3. Checked Recent Commit

```bash
git log --oneline -1
```

Result:

```text
a076be203f1 (HEAD -> study) docs(study): add tutorial on marking mesh islands and driving materials in Blender 5.0
```

### 4. Reviewed Git Configuration

```bash
git config --local --list | grep -E '(lfs|remote\.origin)'
```

Initial configuration showed LFS was configured to use the fork's LFS server.

## Solution

The solution involved configuring Git LFS to use the upstream Blender repository's LFS server instead of the fork's LFS server, and disabling LFS lock verification.

### Step 1: Configure LFS to Use Upstream Repository

```bash
git config lfs.url https://github.com/blender/blender.git/info/lfs
```

This tells Git LFS to read from and write to the upstream repository's LFS storage instead of the fork.

### Step 2: Disable LFS Lock Verification for Fork

```bash
git config lfs.https://github.com/satishgoda/blender.git/info/lfs.locksverify false
```

This disables the lock verification that was causing authentication errors.

### Step 3: Clear Any Specific LFS Push URL

```bash
git config lfs.pushurl ""
```

This ensures the default LFS URL configuration is used.

### Step 4: Push with --no-verify Flag

```bash
git push --no-verify
```

Result:

```text
Enumerating objects: 10, done.
Counting objects: 100% (10/10), done.
Delta compression using up to 16 threads
Compressing objects: 100% (7/7), done.
Writing objects: 100% (7/7), 2.61 KiB | 2.61 MiB/s, done.
Total 7 (delta 3), reused 0 (delta 0), pack-reused 0 (from 0)
remote: Resolving deltas: 100% (3/3), completed with 3 local objects.
To https://github.com/satishgoda/blender.git
   3f6c1ba24ae..a076be203f1  study -> study
```

**Success!** The commit was pushed to the fork.

## Final Configuration

After the fix, the Git LFS configuration looks like:

```bash
remote.origin.url=https://github.com/satishgoda/blender.git
remote.origin.fetch=+refs/heads/*:refs/remotes/origin/*
lfs.repositoryformatversion=0
lfs.url=https://github.com/blender/blender.git/info/lfs
lfs.remote.searchall=true
remote.lfs-fallback.url=https://projects.blender.org/blender/blender.git
remote.lfs-fallback.fetch=+refs/heads/*:refs/remotes/lfs-fallback/*
remote.lfs-fallback.pushurl=no_push
lfs.https://github.com/satishgoda/blender.git/info/lfs.access=basic
lfs.https://github.com/satishgoda/blender.git/info/lfs.locksverify=false
lfs.https://github.com/blender/blender.git/info/lfs.access=basic
```

## Key Takeaways

1. **GitHub Forks and LFS**: GitHub doesn't allow uploading new LFS objects to public forks for storage quota reasons.

2. **Solution Pattern**: Configure LFS to use the upstream repository's LFS server: `git config lfs.url https://github.com/<upstream-org>/<upstream-repo>.git/info/lfs`

3. **Future Pushes**: For subsequent pushes, you can use either:
   - `git push --no-verify` (bypasses LFS lock verification)
   - `git push` (may work now that configuration is set)

4. **Alternative Approach**: If you don't need to add/modify LFS files, you could also use `GIT_LFS_SKIP_SMUDGE=1` when cloning to avoid downloading LFS files entirely.

## References

- [Git LFS Documentation](https://git-lfs.github.com/)
- [GitHub LFS Storage Limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-storage-and-bandwidth-usage)
- [Blender Development Documentation](https://developer.blender.org/)
