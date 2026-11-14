"""Cross-platform launcher used by start.* and reset-demo-data.* (standard library only).

    python scripts/launcher.py start    # set up venv + dependencies, start the app, open the browser
    python scripts/launcher.py reset    # set up venv + dependencies, replace the data with the demo data (seed.py)
    python scripts/launcher.py test     # check the test dependencies (asks before installing), run backend/test_app.py

Options:  --no-browser (start)   --yes (reset: skip the question; test: install without asking)
          --no-install (test: do not ask, run with what is installed)

Setup is idempotent: the virtual environment (venv/) and the packages in requirements.txt are only
created/installed when missing or out of date. Your data (inventory.db) is never touched by `start`.
"""
import hashlib
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV = ROOT / "venv"
REQS = ROOT / "requirements.txt"
STAMP = VENV / ".requirements.sha256"
MIN_PYTHON = (3, 8)
IS_WINDOWS = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
DATA_DIR = ROOT / "database"            # inventory.db, schema.sql, seed.py, migrate.py, backups/
BACKEND = ROOT / "backend"             # app.py, test_app.py
DB_PATH = Path(os.environ.get("INVENTORY_DB") or (DATA_DIR / "inventory.db"))


def say(msg=""):
    print(msg, flush=True)


def fail(msg):
    say(f"\nERROR: {msg}")
    sys.exit(1)


def venv_works():
    if not VENV_PY.exists():
        return False
    try:
        return subprocess.run([str(VENV_PY), "-c", "import sys"], capture_output=True).returncode == 0
    except OSError:
        return False


def ensure_venv():
    if venv_works():
        return
    if VENV.exists():
        # Broken, or made on another OS (the folder travels with the project). Only remove a real venv.
        if (VENV / "pyvenv.cfg").exists():
            say("Existing venv/ does not work on this computer - recreating it.")
            shutil.rmtree(VENV)
        else:
            fail(f"{VENV} exists but is not a virtual environment. Rename or delete it and run again.")
    say("Creating virtual environment (venv/) ...")
    r = subprocess.run([sys.executable, "-m", "venv", str(VENV)])
    if r.returncode != 0 or not venv_works():
        if VENV.exists() and (VENV / "pyvenv.cfg").exists():
            shutil.rmtree(VENV, ignore_errors=True)
        fail("Could not create the virtual environment. On Ubuntu/Debian install it with: "
             "sudo apt install python3-venv python3-pip")


def requirements_hash():
    return hashlib.sha256(REQS.read_bytes()).hexdigest()


def deps_ok():
    if subprocess.run([str(VENV_PY), "-c", "import flask"], capture_output=True).returncode != 0:
        return False
    try:
        return STAMP.read_text().strip() == requirements_hash()
    except OSError:
        return False


def ensure_deps():
    if deps_ok():
        return
    say("Installing dependencies from requirements.txt ...")
    r = subprocess.run([str(VENV_PY), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQS)])
    if r.returncode != 0:
        fail("Dependency install failed. Check your internet connection and run again.")
    STAMP.write_text(requirements_hash())


def setup(install_deps=True):
    if sys.version_info < MIN_PYTHON:
        fail("Python %d.%d or newer is required (found %s)." % (MIN_PYTHON + (sys.version.split()[0],)))
    try:
        import sqlite3 as _s  # noqa: F401
    except ImportError:
        fail("This Python was built without SQLite support (the sqlite3 module). Install a standard Python.")
    ensure_venv()
    if install_deps:
        ensure_deps()


def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def open_browser_when_ready(port):
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):  # up to ~20 seconds
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.2)
    else:
        return
    try:
        webbrowser.open(url)
    except Exception:
        pass


def start(no_browser):
    port = next((p for p in range(5000, 5100) if port_is_free(p)), None)
    if port is None:
        fail("No free port found between 5000 and 5099.")
    if not no_browser:
        threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    say("Starting the Hardware Inventory ... (close this window or press Ctrl+C to stop)\n")
    try:
        return subprocess.call([str(VENV_PY), str(BACKEND / "app.py"), "--port", str(port)], cwd=str(ROOT))
    except KeyboardInterrupt:
        return 0


def asset_count():
    if not DB_PATH.exists():
        return 0
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            return conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        return 0


def reset(assume_yes):
    existing = asset_count()
    backup = None
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        say(f"Data file: {DB_PATH}")
        if existing and not assume_yes:
            say(f"It holds {existing} assets. Resetting ERASES them and loads the demo data (40 assets).")
            say("A backup copy of the current data is saved in the database/backups/ folder first.")
            if input("Type YES to continue: ").strip() != "YES":
                say("Cancelled. Nothing was changed.")
                return 0
        backups_dir = DATA_DIR / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backups_dir / f"inventory.before-reset-{stamp}.db"
        shutil.copy2(DB_PATH, backup)
    # Same as `python database/seed.py`, minus its own YES question (already answered above).
    r = subprocess.run([str(VENV_PY), "-c", "import sys; sys.path.insert(0, 'database'); import seed; seed.main()"], cwd=str(ROOT))
    if r.returncode != 0:
        if backup:
            say(f"Seeding failed. Your previous data is still in database/backups/{backup.name}.")
        return r.returncode
    if backup:
        say(f"Previous data backed up as database/backups/{backup.name} (delete it if you do not need it).")
    say("Done. Demo data restored.")
    return 0


# ---- tests: look for the packages the tests use, ask before installing anything ----------------------
# Counts come from running test_app.py with each package missing (version 21: 293 checks in total).
TEST_TOTAL = 293


def installed_modules():
    """Which of the modules the tests use can the venv's Python import? (nothing is installed or changed)"""
    code = ("import importlib.util as u;"
            "print(' '.join(m for m in ('flask','segno','numpy','zxingcpp','cv2') if u.find_spec(m)))")
    r = subprocess.run([str(VENV_PY), "-c", code], capture_output=True, text=True)
    return set(r.stdout.split())


def ask_yes_no(question):
    while True:
        try:
            answer = input(question + " [Y/N]: ").strip().lower()
        except EOFError:           # no keyboard attached (piped input): the safe answer is No
            say("N")
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def pip_install(args):
    r = subprocess.run([str(VENV_PY), "-m", "pip", "install", "--disable-pip-version-check"] + args)
    return r.returncode == 0


def run_tests(assume_yes, no_install):
    have = installed_modules()
    say("Checking the packages the tests use (in venv/) ...")
    have_decoder = "zxingcpp" in have or "cv2" in have
    missing_required = [(m, n) for m, n in (("flask", "Flask"), ("segno", "segno")) if m not in have]
    need_optional = []                      # pip package names
    if "numpy" not in have:
        need_optional.append("numpy")
    if not have_decoder:
        need_optional.append("zxing-cpp")

    say("  [%s] Flask      - the app itself; without it NO test can run" % ("ok" if "flask" in have else "MISSING"))
    say("  [%s] segno      - draws the QR codes; without it 9 tests FAIL and the QR decode test (1) cannot run"
        % ("ok" if "segno" in have else "MISSING"))
    say("  [%s] numpy + zxing-cpp (or OpenCV) - optional; without them 1 test (QR decode check) is skipped"
        % ("ok" if not need_optional else "MISSING"))

    install = []                            # pip arguments, one list per install step
    if missing_required:
        install.append(["-r", str(REQS)])
    if need_optional:
        install.append(need_optional)

    if install:
        names = [n for _, n in missing_required] + need_optional
        affected = TEST_TOTAL if "flask" not in have else (
            (9 + 1 if "segno" not in have else 0) + (1 if need_optional and "segno" in have else 0))
        say("")
        if "flask" not in have:
            say("WARNING: without Flask the tests cannot run at all.")
        else:
            say("WARNING: without %s, %d of %d tests would fail or be skipped." % (", ".join(names), affected, TEST_TOTAL))
        say("Installing needs internet and downloads from the Python package index (pypi.org) into venv/ only.")
        say("Nothing outside this project folder is changed.")
        if no_install:
            go = False
        elif assume_yes:
            go = True
        else:
            go = ask_yes_no("Download and install %s now?" % ", ".join(names))
        if go:
            for step in install:
                if not pip_install(step):
                    say("\nInstall failed (check your internet connection). Continuing without it.")
                    break
            else:
                if missing_required:
                    STAMP.write_text(requirements_hash())
            have = installed_modules()
        else:
            say("Skipped. Running the tests without them.")
    else:
        say("All test packages are installed.")

    if "flask" not in have:
        say("\nERROR: Flask is not installed, so the tests cannot run. Run this again and answer Y.")
        return 1
    say("\nRunning backend/test_app.py ...\n")
    code = subprocess.call([str(VENV_PY), str(BACKEND / "test_app.py")], cwd=str(ROOT))
    skipped = []
    if "segno" not in have:
        skipped.append("segno is missing: 9 tests failed and 1 was not run (QR codes)")
    if "numpy" not in have or not ("zxingcpp" in have or "cv2" in have):
        if "segno" in have:
            skipped.append("numpy / QR decoder is missing: 1 test was not run (QR decode check), so the total is %d" % (TEST_TOTAL - 1))
    for line in skipped:
        say("Note: " + line + ". Run this script again and answer Y to install it.")
    return code


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if len(args) != 1 or args[0] not in ("start", "reset", "test"):
        fail("usage: launcher.py start|reset|test [--no-browser] [--yes] [--no-install]")
    os.chdir(ROOT)
    if args[0] == "test":
        setup(install_deps=False)           # only makes venv/; packages are installed after asking
        return run_tests("--yes" in flags, "--no-install" in flags)
    setup()
    if args[0] == "start":
        return start("--no-browser" in flags or bool(os.environ.get("NO_BROWSER")))
    return reset("--yes" in flags)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
