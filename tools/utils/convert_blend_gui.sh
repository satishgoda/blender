#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Assuming the script is in tools/utils, the root is two levels up
WORKSPACE_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
VENV_PYTHON="$WORKSPACE_ROOT/.venv/bin/python"
CONVERTER_SCRIPT="$SCRIPT_DIR/blend2json.py"

# Check if Python environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Python virtual environment not found at $VENV_PYTHON"
    exit 1
fi

# Use AppleScript to open a file picker dialog
# We use 'try' block to handle the "User canceled" error gracefully
FILE=$(osascript -e 'try' \
                 -e 'POSIX path of (choose file with prompt "Select .blend file" of type {"blend"})' \
                 -e 'on error' \
                 -e 'return ""' \
                 -e 'end try')

if [ -z "$FILE" ]; then
    echo "No file selected."
    exit 0
fi

echo "Selected file: $FILE"
echo "Running conversion..."

"$VENV_PYTHON" "$CONVERTER_SCRIPT" "$FILE"
