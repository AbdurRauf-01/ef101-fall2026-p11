#!/bin/bash
# Double-click on macOS: choose 1 reset to the 40 demo assets or 2 delete all data (asks first, keeps a backup copy).
cd "$(dirname "$0")" || exit 1
LAUNCHER_PAUSE=1 exec bash scripts/bootstrap.sh reset
