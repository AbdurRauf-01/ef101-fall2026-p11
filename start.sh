#!/usr/bin/env bash
# Fedora / Ubuntu: checks Python and the packages (asks before installing anything), then starts the Hardware Inventory.
# Your data stays in the database/ folder (inventory.db) and is never deleted by launching.
cd "$(dirname "$0")" || exit 1
exec bash scripts/bootstrap.sh start
