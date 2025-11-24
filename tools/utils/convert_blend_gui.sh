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

GUI_SCRIPT="$SCRIPT_DIR/blend2json_gui.py"

# Run the GUI script, passing any arguments (like a file path)
"$VENV_PYTHON" "$GUI_SCRIPT" "$@"

