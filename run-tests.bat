@echo off
REM Double-click on Windows: checks the packages the tests use (asks before installing any), then runs backend/test_app.py.
REM Uses a temporary database; your data (database/inventory.db) is never touched.
call "%~dp0scripts\bootstrap.bat" test
