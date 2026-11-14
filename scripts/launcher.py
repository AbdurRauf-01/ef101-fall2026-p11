"""Cross-platform launcher used by start.* and reset-data.* (standard library only).

    python scripts/launcher.py start    # check the packages, start the app, open the browser
    python scripts/launcher.py reset    # menu: 1 reset to demo data (seed.py), 2 delete all data; needs no extra package
    python scripts/launcher.py test     # check the test packages, run backend/test_app.py

If every package is already installed (in venv/ or system-wide) the app simply starts. Otherwise a menu asks:
    1 install automatically into venv/ (default)   2 install yourself, system-wide (official links are shown)
    3 continue anyway (may stop with an error)     4 exit
Nothing is installed without that choice. Your data (inventory.db) is never touched by `start`.

Options:  --no-browser (start)   --yes (reset: demo data without asking; test: same as menu choice 1)   --demo / --empty (reset: pick 1 / 2)
          --no-install (test: same as menu choice 3)      LAUNCHER_CHOICE=1..4 in the environment picks a menu choice
"""
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
MIN_PYTHON = (3, 8)
IS_WINDOWS = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")
DATA_DIR = ROOT / "database"            # inventory.db, schema.sql, seed.py, migrate.py, backups/
BACKEND = ROOT / "backend"             # app.py, test_app.py
DB_PATH = Path(os.environ.get("INVENTORY_DB") or (DATA_DIR / "inventory.db"))

# Packages: import name -> (pip name, minimum version). zxingcpp / cv2 are alternatives (QR decoding, tests only).
APP_PACKAGES = ("flask", "segno")                  # needed to run the app
TEST_PACKAGES = ("flask", "segno", "numpy", "decoder")   # needed for every test to run (decoder = zxingcpp or cv2)
PIP_NAMES = {"flask": "Flask", "segno": "segno", "numpy": "numpy", "decoder": "zxing-cpp"}
PIP_PAGES = {"Flask": "https://pypi.org/project/Flask/", "segno": "https://pypi.org/project/segno/",
             "numpy": "https://pypi.org/project/numpy/", "zxing-cpp": "https://pypi.org/project/zxing-cpp/"}
PYTHON_PAGE = "https://www.python.org/downloads/"
# Counts come from running test_app.py with each package missing (version 23: 313 checks in total).
TEST_TOTAL = 313

# Run inside each candidate Python: which of the packages can it import (and is Flask/segno new enough)?
PROBE = (
    "import importlib.util as u\n"
    "from importlib import metadata as md\n"
    "mins = {'flask': (2, 2), 'segno': (1, 5)}\n"
    "out = []\n"
    "for m in ('flask', 'segno', 'numpy', 'zxingcpp', 'cv2'):\n"
    "    if not u.find_spec(m):\n"
    "        continue\n"
    "    if m in mins:\n"
    "        try:\n"
    "            v = tuple(int(x) for x in md.version(m).split('.')[:2])\n"
    "        except Exception:\n"
    "            v = mins[m]\n"
    "        if v < mins[m]:\n"
    "            continue\n"
    "    out.append(m)\n"
    "print(' '.join(out))\n"
)


class SetupError(Exception):
    pass


def say(msg=""):
    print(msg, flush=True)


def fail(msg):
    say(f"\nERROR: {msg}")
    sys.exit(1)


def pip_cmd(py):
    # --only-binary: take ready-made wheels only, so no package can run build scripts on this computer.
    return [str(py), "-m", "pip", "install", "--disable-pip-version-check", "--only-binary=:all:"]


# ---- which Python can run the app? -------------------------------------------------------------------
def modules_of(py):
    """Set of the wanted packages this Python can import, or None if it cannot be run. Nothing is changed."""
    try:
        r = subprocess.run([str(py), "-c", PROBE], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    found = set(r.stdout.split())
    if "zxingcpp" in found or "cv2" in found:
        found.add("decoder")
    return found


def candidate_pythons():
    """venv/ first, then the system Python(s): the one running this script and the ones on PATH."""
    seen, out = set(), []
    for p in (VENV_PY, sys.executable, getattr(sys, "_base_executable", None),
              shutil.which("python3"), shutil.which("python")):
        if not p:
            continue
        key = os.path.normcase(os.path.abspath(str(p)))
        if key in seen or not os.path.exists(str(p)):
            continue
        seen.add(key)
        out.append(Path(p))
    return out


def complete(have, needed):
    return all(n in have for n in needed)


def survey():
    return [(p, have) for p in candidate_pythons() for have in [modules_of(p)] if have is not None]


def best_of(found, needed):
    """The first complete Python, else the one with most packages (venv/ wins ties)."""
    for p, have in found:
        if complete(have, needed):
            return p, have
    return max(found, key=lambda f: sum(n in f[1] for n in needed)) if found else (Path(sys.executable), set())


def missing_pip_names(have, needed):
    return [PIP_NAMES[n] for n in needed if n not in have]


# ---- venv + automatic install (menu choice 1) --------------------------------------------------------
def venv_works():
    return VENV_PY.exists() and modules_of(VENV_PY) is not None


def ensure_venv():
    if venv_works():
        return
    if VENV.exists():
        # Broken, or made on another OS (the folder travels with the project). Only remove a real venv.
        if (VENV / "pyvenv.cfg").exists():
            say("Existing venv/ does not work on this computer - recreating it.")
            shutil.rmtree(VENV)
        else:
            raise SetupError(f"{VENV} exists but is not a virtual environment. Rename or delete it and run again.")
    say("Creating virtual environment (venv/) ...")
    r = subprocess.run([sys.executable, "-m", "venv", str(VENV)])
    if r.returncode != 0 or not venv_works():
        if VENV.exists() and (VENV / "pyvenv.cfg").exists():
            shutil.rmtree(VENV, ignore_errors=True)
        raise SetupError("Could not create the virtual environment. On Ubuntu/Debian install it with: "
                         "sudo apt install python3-venv python3-pip")


def auto_install(needed):
    """Menu choice 1. Returns True when the packages the app needs are now in venv/."""
    say("\nInstalling into venv/ only (nothing outside this project folder is changed, no administrator rights).")
    say("This needs internet: the packages come from the Python package index (pypi.org), ready-made wheels only.")
    try:
        ensure_venv()
    except SetupError as e:
        say(f"\nERROR: {e}")
        return False
    have = modules_of(VENV_PY) or set()
    required_missing = [n for n in APP_PACKAGES if n not in have]
    if required_missing:
        say("Installing Flask and segno (requirements.txt) ...")
        if subprocess.run(pip_cmd(VENV_PY) + ["-r", str(REQS)]).returncode != 0:
            say("\nThe install failed. Check your internet connection (or choose option 2 and install by hand).")
            return False
    have = modules_of(VENV_PY) or set()
    optional = [PIP_NAMES[n] for n in needed if n not in APP_PACKAGES and n not in have]
    if optional:
        say("Installing the optional test packages (%s) ..." % ", ".join(optional))
        if subprocess.run(pip_cmd(VENV_PY) + optional).returncode != 0:
            say("The optional packages could not be installed here; the tests run without them.")
    return complete(modules_of(VENV_PY) or set(), APP_PACKAGES)


# ---- the menu ------------------------------------------------------------------------------------------
def ask_choice(preset):
    if preset in ("1", "2", "3", "4"):
        say(f"Choice {preset} (preset).")
        return preset
    while True:
        try:
            answer = input("Choose 1-4 [1]: ").strip()
        except EOFError:           # no keyboard attached: do nothing rather than install without asking
            say("\nNo keyboard input, so nothing was installed. Run again in a terminal, or set LAUNCHER_CHOICE=1.")
            return "4"
        if answer == "":
            return "1"
        if answer in ("1", "2", "3", "4"):
            return answer


def ask_yes_no(question):
    while True:
        try:
            answer = input(question + " [Y/N]: ").strip().lower()
        except EOFError:
            say("N")
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False


def show_manual_steps(have, needed):
    base = getattr(sys, "_base_executable", None) or sys.executable
    names = missing_pip_names(have, needed)
    say("\nInstall the missing items yourself. Download only from the official sites below.")
    say("")
    say(f"  Python (3.8 or newer; you are using {sys.version.split()[0]}):  {PYTHON_PAGE}")
    say("    Windows: choose \"Install just for me\" (no administrator rights needed) and tick \"Add python.exe to PATH\".")
    say("    Windows installer: right-click > Properties > Digital Signatures must show \"Python Software Foundation\".")
    say("  Packages still missing: " + (", ".join(names) if names else "none"))
    for n in names:
        say(f"    {n}: {PIP_PAGES[n]}")
    if names:
        say("")
        say("  Install them for your user account with this Python (no administrator / sudo needed):")
        say(f"    \"{base}\" -m pip install --user --only-binary=:all: " + " ".join(
            ('"Flask>=2.2"' if n == "Flask" else '"segno>=1.5"' if n == "segno" else n) for n in names))
        say("  Newer Ubuntu, Debian and Fedora may answer \"externally-managed-environment\". Then do not force it:")
        say("  go back and choose option 1 (venv/) instead.")
    say("")
    say("  Safer this way: nothing runs with administrator rights, nothing is downloaded by this script, and")
    say("  --only-binary stops any package from running build scripts.")


def show_missing(action, have, needed):
    say("")
    if action == "test":
        say("Checking the packages the tests use ...")
        say("  [%s] Flask      - the app itself; without it NO test can run" % ("ok" if "flask" in have else "MISSING"))
        say("  [%s] segno      - draws the QR codes; without it 9 tests FAIL and the QR decode test (1) cannot run"
            % ("ok" if "segno" in have else "MISSING"))
        say("  [%s] numpy + zxing-cpp (or OpenCV) - optional; without them 1 test (QR decode check) is skipped"
            % ("ok" if "numpy" in have and "decoder" in have else "MISSING"))
        names = missing_pip_names(have, needed)
        if "flask" not in have:
            say("\nWARNING: without Flask the tests cannot run at all.")
        else:
            affected = (10 if "segno" not in have else 0) + (1 if ("segno" in have and
                        ("numpy" not in have or "decoder" not in have)) else 0)
            say("\nWARNING: without %s, %d of %d tests would fail or be skipped." % (", ".join(names), affected, TEST_TOTAL))
    else:
        names = missing_pip_names(have, needed)
        say("Missing: " + ", ".join(names))
        if "flask" not in have:
            say("Without Flask the app cannot start.")
        elif "segno" not in have:
            say("Without segno the app starts, but QR labels do not work.")
    say(f"Official sources: Python {PYTHON_PAGE}  -  packages https://pypi.org/")


def resolve_python(action, needed, preset=None):
    """Return the Python to run with, or None when the user chose Exit. Asks before installing anything."""
    preset = preset or os.environ.get("LAUNCHER_CHOICE", "").strip() or None
    tried_auto = False
    after_manual = False
    while True:
        found = survey()
        py, have = best_of(found, needed)
        if complete(have, needed):
            return py
        if tried_auto and complete(have, APP_PACKAGES) and py == VENV_PY:
            return py                     # the optional test packages could not be installed; carry on without them
        if after_manual:
            say("\nChecked again: the packages were not found by the Python that runs this script.")
            after_manual = False
        show_missing(action, have, needed)
        say("")
        say("  1. Install the dependencies automatically into venv/ (default; needs internet)")
        say("  2. Install them yourself, system-wide (shows the official links first)")
        say("  3. Continue anyway (may stop with an error)")
        say("  4. Exit")
        choice = ask_choice(preset)
        preset = None
        if choice == "1":
            tried_auto = True
            if auto_install(needed):
                continue
            tried_auto = False
        elif choice == "2":
            show_manual_steps(have, needed)
            say("")
            if ask_yes_no("Done installing? Y = check again and launch, N = back to the menu"):
                after_manual = True
                continue
        elif choice == "3":
            say("\nContinuing without everything. If something stops with an error, run this again and pick 1 or 2.")
            return py
        else:
            say("Exited. Nothing was installed.")
            return None


# ---- start / reset ---------------------------------------------------------------------------------------
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


def start(py, no_browser):
    port = next((p for p in range(5000, 5100) if port_is_free(p)), None)
    if port is None:
        fail("No free port found between 5000 and 5099.")
    if not no_browser:
        threading.Thread(target=open_browser_when_ready, args=(port,), daemon=True).start()
    say("Starting the Hardware Inventory ... (close this window or press Ctrl+C to stop)\n")
    try:
        return subprocess.call([str(py), str(BACKEND / "app.py"), "--port", str(port)], cwd=str(ROOT))
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


def reset(py, flags):
    """Option 1: demo data (seed.py). Option 2: delete all data (empty database with the six standard places)."""
    assume_yes = "--yes" in flags
    mode = "demo" if "--demo" in flags else "empty" if "--empty" in flags else "demo" if assume_yes else None
    if mode is None:
        say("What do you want to do with the data?")
        say("")
        say("  1. Reset to demo data (40 demo assets and their fault history)")
        say("  2. Delete all data (empty database with the six standard places, ready for your own assets)")
        say("")
        try:
            answer = input("Choose 1 or 2 (Enter cancels): ").strip()
        except EOFError:
            answer = ""
        if answer not in ("1", "2"):
            say("Cancelled. Nothing was changed.")
            return 0
        mode = "demo" if answer == "1" else "empty"
    existing = asset_count()
    backup = None
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        say(f"Data file: {DB_PATH}")
        if existing and not assume_yes:
            if mode == "demo":
                say(f"It holds {existing} assets. Resetting ERASES them and loads the demo data (40 assets).")
            else:
                say(f"It holds {existing} assets. This DELETES every asset, fault, repair step and maintenance record "
                    "(only the six standard places stay).")
            say("A backup copy of the current data is saved in the database/backups/ folder first.")
            try:
                confirmed = input("Type YES to continue: ").strip() == "YES"
            except EOFError:
                confirmed = False
            if not confirmed:
                say("Cancelled. Nothing was changed.")
                return 0
        backups_dir = DATA_DIR / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backups_dir / f"inventory.before-{'reset' if mode == 'demo' else 'delete'}-{stamp}.db"
        shutil.copy2(DB_PATH, backup)
    if mode == "demo":
        # Same as `python database/seed.py`, minus its own YES question (already answered above).
        code = "import sys; sys.path.insert(0, 'database'); import seed; seed.main()"
    else:
        code = "import sys; sys.path.insert(0, 'database'); import db; db.empty_database()"
    r = subprocess.run([str(py), "-c", code], cwd=str(ROOT))
    if r.returncode != 0:
        if backup:
            say(f"The change failed. Your previous data is still in database/backups/{backup.name}.")
        return r.returncode
    if backup:
        say(f"Previous data backed up as database/backups/{backup.name} (delete it if you do not need it).")
    say("Done. Demo data restored." if mode == "demo" else "Done. All data deleted; the six standard places are back. Add assets from the app.")
    return 0


# ---- tests -------------------------------------------------------------------------------------------------
def run_tests(py, have):
    if "flask" not in have:
        say("\nERROR: Flask is not installed, so the tests cannot run. Run this again and pick 1 or 2.")
        return 1
    say("\nRunning backend/test_app.py ...\n")
    code = subprocess.call([str(py), str(BACKEND / "test_app.py")], cwd=str(ROOT))
    if "segno" not in have:
        say("Note: segno is missing: 9 tests failed and 1 was not run (QR codes). Run this again and pick 1 or 2 to install it.")
    elif "numpy" not in have or "decoder" not in have:
        say("Note: numpy / a QR decoder is missing: 1 test was not run (QR decode check), so the total is %d. "
            "Run this again and pick 1 or 2 to install it." % (TEST_TOTAL - 1))
    return code


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if len(args) != 1 or args[0] not in ("start", "reset", "test"):
        fail("usage: launcher.py start|reset|test [--no-browser] [--yes] [--no-install]")
    if sys.version_info < MIN_PYTHON:
        fail("Python %d.%d or newer is required (found %s)." % (MIN_PYTHON + (sys.version.split()[0],)))
    try:
        __import__("sqlite3")             # only checks that the module exists
    except ImportError:
        fail("This Python was built without SQLite support (the sqlite3 module). Install a standard Python.")
    os.chdir(ROOT)
    action = args[0]
    if action == "reset":                    # seed.py uses only the standard library: no package is needed
        return reset(Path(sys.executable), flags)
    preset = None
    if action == "test":
        preset = "1" if "--yes" in flags else "3" if "--no-install" in flags else None
    needed = TEST_PACKAGES if action == "test" else APP_PACKAGES
    py = resolve_python(action, needed, preset)
    if py is None:
        return 0
    if action == "start":
        return start(py, "--no-browser" in flags or bool(os.environ.get("NO_BROWSER")))
    return run_tests(py, modules_of(py) or set())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
