#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Add src directory to PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"

# Echo the current PYTHONPATH for verification
echo "PYTHONPATH is now set to: $PYTHONPATH" 