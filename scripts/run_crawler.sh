#!/bin/bash

# Source the environment setup script
source "$(dirname "$0")/setup_env.sh"

# Forward all arguments to the crawler script
python src/crawler.py "$@" 