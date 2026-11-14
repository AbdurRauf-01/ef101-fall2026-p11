#!/usr/bin/env bash
# Fedora / Ubuntu: checks the packages the tests use (asks before installing any), then runs backend/test_app.py.
# Uses a temporary database; your data (database/inventory.db) is never touched.
cd "$(dirname "$0")" || exit 1
exec bash scripts/bootstrap.sh test
