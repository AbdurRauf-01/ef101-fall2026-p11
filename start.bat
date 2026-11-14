@echo off
REM Double-click on Windows: checks Python and the packages (asks before installing anything), then starts the Hardware Inventory.
REM Your data stays in the database/ folder (inventory.db) and is never deleted by launching.
call "%~dp0scripts\bootstrap.bat" start
