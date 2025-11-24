#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$REPO_ROOT/.venv/bin/python"
VENV_IPYTHON="$REPO_ROOT/.venv/bin/ipython"
VENV_JUPYTER="$REPO_ROOT/.venv/bin/jupyter"
if [[ ! -x "$VENV_PYTHON" || ! -x "$VENV_IPYTHON" || ! -x "$VENV_JUPYTER" ]]; then
  echo "Python virtual environment, IPython, or Jupyter binary not found in $REPO_ROOT/.venv" >&2
  echo "Run: /opt/homebrew/bin/python3.11 -m venv .venv && ./.venv/bin/pip install jupyter" >&2
  exit 1
fi
B3D_BPY_PREFIX_DEFAULT="/Users/sgoda/dev/b3d/blender_build/install"
B3D_BPY_PREFIX="${B3D_BPY_PREFIX:-$B3D_BPY_PREFIX_DEFAULT}"
B3D_BPY_PACKAGE_DIR="$B3D_BPY_PREFIX/bpy"
if [[ ! -d "$B3D_BPY_PACKAGE_DIR" ]]; then
  echo "Standalone bpy install not found at $B3D_BPY_PACKAGE_DIR" >&2
  echo "Make sure you've run: make bpy ..." >&2
  exit 1
fi

version_dir=""
while IFS= read -r -d '' candidate; do
  base_name="$(basename "$candidate")"
  if [[ "$base_name" =~ ^[0-9]+\.[0-9]+$ ]]; then
    version_dir="$candidate"
    break
  fi
done < <(find "$B3D_BPY_PACKAGE_DIR" -mindepth 1 -maxdepth 1 -type d -print0)

if [[ -z "$version_dir" ]]; then
  echo "Unable to locate versioned bpy data directory inside $B3D_BPY_PACKAGE_DIR" >&2
  exit 1
fi

python_site="$version_dir/python/lib/python3.11/site-packages"
scripts_dir="$version_dir/scripts/modules"
extra_paths=("$B3D_BPY_PREFIX" "$B3D_BPY_PACKAGE_DIR" "$python_site" "$scripts_dir")

joined_paths=""
for path in "${extra_paths[@]}"; do
  if [[ -d "$path" || -f "$path" ]]; then
    if [[ -z "$joined_paths" ]]; then
      joined_paths="$path"
    else
      joined_paths="$joined_paths:$path"
    fi
  fi
done

if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="$joined_paths:$PYTHONPATH"
else
  export PYTHONPATH="$joined_paths"
fi

if [[ $# -gt 0 ]]; then
  case "$1" in
    qtconsole|notebook|lab|labextension|console|kernel|kernelspec|nbconvert|nbclassic|server|run)
      exec "$VENV_JUPYTER" "$@"
      ;;
  esac
fi

exec "$VENV_IPYTHON" "$@"
