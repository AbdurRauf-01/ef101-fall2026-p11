# EF101-P11 Computer Hardware Inventory and Maintenance System

> # **Project History Notice:** 
> ## For all commits, and project history prior to **November 9, 2026**, please visit the legacy repository: [AbdurRauf-01/ef101-p11](https://github.com/AbdurRauf-01/ef101-p11).

## Version history

- **Version 20 and after (from 12 Nov 2026):** see [`CHANGELOG.md`](https://github.com/AbdurRauf-01/ef101-fall2026-p11/blob/main/CHANGELOG.md) in this repository.
- **Version 19 (9 Nov 2026):** see the [`changelogs`](https://github.com/AbdurRauf-01/ef101-fall2026-p11/tree/main/changelogs) directory in this repository (`v19.md`).
- **Version 18 and before:** see the [`changelogs`](https://github.com/AbdurRauf-01/ef101-p11/tree/main/changelogs) directory in the legacy repository.

Flask + SQLite web app that tracks computer assets (specs, location, warranty, status) and their maintenance/fault history, with a dashboard and CSV export. All data in `inventory.db` is **DEMO data**, not real assets.

## Project schema

Project schema

## Run

**Two-click launch** (installs Python and the packages first if they are missing; needs internet the first time):

|  | Start the app | Reset to demo data |
| --- | --- | --- |
| Windows | `start.bat` | `reset-demo-data.bat` |
| macOS | `start.command` | `reset-demo-data.command` |
| Fedora / Ubuntu | `start.sh` | `reset-demo-data.sh` |

Double-click the file (Linux: if your file manager only opens it in an editor, run `./start.sh` in a terminal, or set the file manager to "Run in terminal"). The app opens in your browser. If a copy lost its executable bit, run `chmod +x *.command *.sh scripts/*.sh` once.

What the launcher does: finds Python 3.8+ (installs it with winget/python.org on Windows, Homebrew/python.org on macOS, dnf on Fedora, apt on Ubuntu), creates `venv/`, installs `requirements.txt` into it, then starts `app.py`. Later launches skip every step that is already done. `venv/` can be deleted at any time; it is rebuilt automatically. Manual run: see "Manual run (no launcher)" below.

**Reset to demo data** asks you to type YES, saves the current data as `inventory.before-reset-<date>.db`, then does the same as `python seed.py`. The app prints its address (http://127.0.0.1:5000, or the next free port if 5000 is busy) and the location of its data file.

- **Your data is kept in this folder**, in `inventory.db`. Launching never deletes it. To move the project, move the whole folder, data included.
- **First launch:** an empty database is created with the six standard places. Add assets from the app.
- **Demo data (optional):** `python seed.py` replaces the data with 40 demo assets. It asks you to type YES first when there is data.
- **Several copies at once:** each copy has its own data file and its own address, so you can run an older version (for example v7) next to this one to compare.
- **Tests:** `python test_app.py` runs every check (285 in version 20) on a temporary database and prints a results table.

## Manual run (no launcher)

Use this to open the project by hand after getting it from GitHub (main branch), or if the two-click launcher does not work on your computer. All commands are typed in a terminal opened **inside the project folder** (the folder that contains `app.py`).

1. **Get the project.** Either:
   - **Clone:** `git clone https://github.com/AbdurRauf-01/ef101-fall2026-p11.git`, which creates the folder `ef101-fall2026-p11`; or
   - **Download ZIP:** on the GitHub page of the repository (main branch) click Code, then Download ZIP, and extract it. The extracted folder is usually named `ef101-fall2026-p11-main`.

   `inventory.db` (the demo data) comes with the project. The `venv/` folder does not, so you create it in step 4.
2. **Install Python 3.8 or newer** (https://www.python.org/downloads/; on Windows tick "Add python.exe to PATH" in the installer). Check it: `python --version` (on macOS/Linux the command may be `python3 --version`). Ubuntu also needs `sudo apt install python3-venv python3-pip`; Fedora usually has them already.
3. **Open a terminal in the project folder.** Windows: open the folder in File Explorer, click the address bar, type `cmd`, press Enter (or right-click, "Open in Terminal"). macOS/Linux: open Terminal and `cd` into the folder, for example `cd ~/Downloads/ef101-fall2026-p11-main`. Check you are in the right place with `dir` (Windows) or `ls` (macOS/Linux): you should see `app.py`.
4. **Create the virtual environment** (once only; this makes the `venv/` folder):

   ```
   python -m venv venv          # macOS/Linux: python3 -m venv venv
   ```

5. **Activate it** (every time you open a new terminal):

   | System | Command |
   | --- | --- |
   | Windows (Command Prompt) | `venv\Scripts\activate.bat` |
   | Windows (PowerShell) | `venv\Scripts\Activate.ps1` |
   | macOS / Linux | `source venv/bin/activate` |

   The prompt now starts with `(venv)`. If PowerShell says scripts are disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once in that window and activate again (or use Command Prompt instead).
6. **Install the packages** (once only, needs internet): `pip install -r requirements.txt`
7. **Optional, data:** the shipped `inventory.db` already holds the demo data. To reset it to the demo data, run `python seed.py` (it asks you to type YES). If you copied in an `inventory.db` from an older version, run `python migrate.py` first.
8. **Start the app:** `python app.py` (optional: `python app.py --port 8000` to choose the port).
9. **Open the address it prints** in your browser, normally http://127.0.0.1:5000 (the next free port if 5000 is busy). Use the address shown in your own terminal.
10. **Stop the app** with `Ctrl+C` in the terminal. Leave the virtual environment with `deactivate`.
11. **Run the tests (optional):** with the venv still active, `python test_app.py`. It uses a temporary database, so your data is not touched, and must end with `229/229 passed`.

Next time you only need steps 3, 5 and 8: open the terminal in the folder, activate the venv, run `python app.py`. To get later changes from GitHub, run `git pull` (clone) or download the ZIP again (keep your own `inventory.db` if you want to keep your data).

Common problems: `python` not found (try `python3` or `py`, or reinstall Python with PATH ticked); `No module named flask` (the venv is not active, or step 6 was skipped); `venv` was copied from another computer or another operating system (delete the `venv/` folder and repeat steps 4 to 6); "Address already in use" (the app picks the next free port by itself, or choose one with `--port`).

### Manual run on Linux (Ubuntu and Fedora): all commands in one place

Open a terminal (Ubuntu: Ctrl+Alt+T; Fedora: search for "Terminal"). Do step A once, then B to D.

**A. Install the tools (once).**

| System | Command |
| --- | --- |
| Ubuntu / Debian | `sudo apt update && sudo apt install -y git python3 python3-venv python3-pip` |
| Fedora | `sudo dnf install -y git python3 python3-pip` |

Fedora's `python3` already includes `venv`. Check the version (3.8 or newer): `python3 --version`

**B. Get the project (once).** Either clone it:

```
git clone https://github.com/AbdurRauf-01/ef101-fall2026-p11.git
cd ef101-fall2026-p11
```

or download the ZIP of the main branch from GitHub and extract it (`unzip ef101-fall2026-p11-main.zip`, or right-click, Extract), then `cd` into the folder, for example `cd ~/Downloads/ef101-fall2026-p11-main`. In the file manager you can also right-click inside the folder and choose "Open in Terminal". Check with `ls` that you can see `app.py`.

**C. Create the virtual environment and install Flask (once).**

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**D. Start the app (every time).**

```
cd ef101-fall2026-p11         # or ef101-fall2026-p11-main, the project folder
source venv/bin/activate      # the prompt now starts with (venv)
python app.py
```

Open the printed address (normally http://127.0.0.1:5000) in the browser, or run `xdg-open http://127.0.0.1:5000` from a second terminal. Stop with `Ctrl+C`, then `deactivate`.

Linux notes:
- Inside the activated venv, `python` and `pip` work (the venv provides them). Outside it, use `python3`.
- `The virtual environment was not created successfully` or `ensurepip is not available` on Ubuntu: `python3-venv` is missing; run the Ubuntu command in step A, delete the half-made folder with `rm -rf venv`, and repeat step C.
- `error: externally-managed-environment` when running pip: you are outside the venv. Run `source venv/bin/activate` first; do not use `--break-system-packages`.
- `command not found: git`: install it as in step A, or use the ZIP download instead.
- Optional: `python seed.py` resets the data to the demo data (type YES), and `python test_app.py` runs the 285 checks.
- If a double-click launcher does not run, give it permission once: `chmod +x start.sh reset-demo-data.sh scripts/*.sh`, then `./start.sh`. This manual route does not need it.

## Files

| File | Purpose |
| --- | --- |
| `start.*`, `reset-demo-data.*`, `scripts/` | Launchers per OS: dependency check/install, venv, start, demo reset |
| `requirements.txt` | Python packages (Flask, segno) |
| `app.py` | Backend: routes, input validation, CSV export (no SQL) |
| `qr_labels.py` | The spec text stored in a label, the QR code itself (SVG, made with segno) and the rule that turns a scanned text into an asset ID |
| `queries.py` | Database layer: every SQL statement (filters, saves, dashboard figures) |
| `db.py` | SQLite connection + schema creation |
| `schema.sql` | The four tables: `locations`, `assets`, `fault_steps` (steps of an open fault) and `maintenance` (history) |
| `seed.py` | Demo data generator (fixed random seed, reproducible) |
| `migrate.py` | Upgrades an older `inventory.db` to the current version without losing data (backup kept, safe to run twice) |
| `CHANGELOG.md` | What changed in version 20 (older versions: the `changelogs/` folder on GitHub) |
| `test_app.py` | Test evidence (add, edit, retire, invalid input, duplicates, filters, history, dashboard, export) |
| `templates/`, `static/` | HTML (Jinja) pages and the stylesheet; `static/scan.js` is the Scan page script and `static/vendor/jsQR.js` the bundled QR reader (Apache-2.0, licence beside it) |

## Upgrading an existing database

Only needed if you already have an `inventory.db` from an older version. This version ships with its own up-to-date `inventory.db`, so a fresh copy needs nothing.

Run `python migrate.py` once (or `python migrate.py path/to/inventory.db`). It keeps a backup as `inventory.db.bak` first, checks the new database (row counts, integrity, foreign keys) before replacing the old one, and does nothing if the database is already up to date (running it twice is safe).

- **From version 14-15.x** (the database already has `fault_steps`): everything is kept exactly as it is: assets, places and their range numbers, IP addresses, history, and the steps of open faults. The only change is that steps no longer carry a cost. The cost of an open fault stays on the asset as its single Updated Cost (if an open fault had none, the cost of its last step becomes the Updated Cost). Old steps that only held a cost (no action) are removed.
- **From version 8-13** (no `fault_steps` table): incomplete history entries (a blank or Unknown field) are removed, valid entries logged while a fault was open become its steps, invalid or repeated IP addresses are left as Not Assigned, and everything removed or changed is listed on screen.

## How it works

- **Cost**: A single *Updated Cost* ($) box is used across all forms. Rather than adding up a price for every step, the person entering data controls the current total directly. When a fault is closed to Operational, the final maintenance history entry records this Updated Cost. A typed `0` is a real cost of 0 and is saved as 0 (on the Edit form and on the Log form); a blank box keeps the current total.
- **Editable records**: To fix grammatical mistakes or typos, all items in *Maintenance history*, *Current fault*, and open fault steps can be edited directly.
- **Asset IDs**: Auto-generated from the chosen location (e.g. `L1-PC-041`) if not manually entered. The user can enter a custom Asset ID or simply select the place to have the next available ID assigned automatically.
- **GPU VRAM**: The GPU VRAM input is dynamically displayed only when a dedicated GPU is entered. For machines with integrated graphics (blank GPU), the VRAM field is hidden.
- **Fault history page** (sidebar: Fault History): lists every closed fault of every asset, newest first by default. Click a column heading to sort by it (click again to reverse); the Status heading cycles which status comes first.
- **IP addresses**: optional. The Add/Edit form suggests one from the Asset ID and the place's range: `192.168.{range}.{last two digits of the ID number}` (for example L1-PC-041 in Lab 1 gives 192.168.1.41). The suggestion updates when the ID or place changes. Typing an IP switches to Custom mode, and *Reset to Auto* returns to the suggestion. A blank IP is shown as Not Assigned. Two PCs in the same place can never share an IP (checked on save): if a suggestion repeats one, the save is refused with a message and the IP must be changed. Different places may share one.
- **Needs attention** (active assets only): status is Faulty or Under Repair, and nothing else. Past fault events are listed separately on the Fault History page, whatever the status.
- **Current fault**: while a PC is Faulty or Under Repair, its fault (category, description, actions to be taken, technician, date, updated cost) is shown in its Current fault section. Nothing is written to the history while the fault is open. Under Repair requires a technician. A blank category is saved as Unknown.
- **Steps of an open fault**: each save with a new action adds an audit step (its date, action and technician). A step has no cost of its own: the cost of the open fault is the single Updated Cost, so correcting the cost changes the total and adds no step. The steps are listed under Current fault.
- **Closing a fault**: the PC is closed by setting it to Operational. Every fault field (category other than Unknown, description, action taken, technician) and the date are required; the cost is optional. The fault is then written to the history as ONE entry: its Action taken lists every step with its date, and its cost is the single Updated Cost.
- **Sorting**: the asset list sorts by any column (click a heading; click again to reverse). The Status heading cycles which status comes first: Operational (green), Under Repair (yellow), Faulty (red); the other statuses follow alphabetically. The default is Asset ID, ascending.
- **Fault categories**: maintenance events use a fixed drop-down (Disk failure, Overheating, Network issue, RAM fault, OS corruption, Display issue, PSU failure, Other, Unknown). The failure chart always shows every category; anything unexpected is counted as Other.
- **Locations**: a place is chosen from a drop-down, or added with **+ Add new location** (it then appears on the dashboard, even while empty). Each place has a short code (for example Lab 4 = `L4`).
- **RAM type**: DDR1 to DDR5 drop-down, required for every asset (12th to 14th gen Intel CPUs can take DDR4 or DDR5, so the type is recorded per machine).
- **Dashboard charts** are computed from the same active-asset query as the totals, so the charts always add up to the total.
- **Warranty label**: `WARRANTY_SOON_DAYS` (30) at the top of `queries.py` sets the Expiring soon window.
- **Warranty status** is computed from `warranty_expiry` (Active / Expiring soon / Expired), never stored.
- **Retire** sets `active = 0`; the row and its history are kept. Reactivate reverses it.
- **Validation**: required fields, RAM/storage positive integers, valid IP, valid dates (always stored as YYYY-MM-DD, whatever format was typed), purchase date not in the future, warranty not before purchase, duplicate asset ID rejected (upper/lower case ignored), asset ID of letters, digits, `-` `.` `_` only (max 40), costs finite and between 0 and 1,000,000,000, a text box holds at most 500 characters, a location name at most 40.
- **Local-only protections**: the app answers only to `127.0.0.1` / `localhost` (set `INVENTORY_ALLOWED_HOSTS` to add a name), refuses form posts sent from another website, and sends a Content-Security-Policy so the browser loads nothing from the internet. Debug mode is off; start with `FLASK_DEBUG=1` only when developing.
- **QR labels and scanning** (bonus, version 20): every asset has a QR code holding a short plain-text block of its specs (asset ID, model, CPU, RAM, storage, GPU, OS, IP, location, warranty expiry) and its status with an *as of* date. Any phone camera shows that text with no network, so the specs can be read even though the app runs only on this computer. The text is a snapshot: after a spec or status change the label must be printed again (the printed date shows its age); the asset page in the app is always current. Fault details and costs are never put on a label. The asset page shows the code with *Print label* and *Download SVG*; *QR Labels* in the sidebar (or the *QR labels* button on the Assets list, which keeps the current search and filters) opens a printable sheet of labels (QR, ID, model, place, warranty, printed date). The *Scan QR* page reads a label with the camera, from an uploaded photo, or from the text box (a USB barcode scanner types into it), asks the app which asset the text means (`/api/scan-lookup`; the spec block, an older link, `EF101-ASSET:<ID>` or a bare ID are all understood, upper/lower case ignored) and opens it. Reading happens in the browser, nothing is sent anywhere else. The camera needs `http://127.0.0.1` or `localhost`. The app answers only to 127.0.0.1 and localhost unless `INVENTORY_ALLOWED_HOSTS` is set, so a phone cannot open the app itself; it reads the specs from the code instead. If `segno` is missing the label pages show an install hint and every other page still works.
- **Exports**: CSV cells that start with `=` `+` `-` `@` get a leading apostrophe so Excel/Calc cannot run them as formulas; files carry a UTF-8 byte-order mark so accents open correctly.
- **Old databases**: starting the app on an `inventory.db` from an older version stops with a message to run `python migrate.py`.
- All SQL uses `?` placeholders (no string-built values), so search input cannot inject SQL.

## Tool and AI disclosure

**Software:** Python, Flask, SQLite (built-in `sqlite3`), Jinja templates and plain CSS. The QR codes are drawn by the Python package `segno` (BSD) and read in the browser by `jsQR` (Apache-2.0, one file bundled in `static/vendor/`, so nothing is loaded from the Internet at run time; `segno` is installed from the Python package index with the other requirements). No font, script or image is loaded from the Internet. No external data or assets are used; the demo data is generated by `seed.py`.

**AI:** Claude (Anthropic) was used to draft the application code, the demo-data script, the test script and the report skeleton. Later versions (up to version 20) were improved and fixed using several Claude accounts. Version 19 (9 Nov 2026) changed the interface styling, sidebar counts and the Credits, Privacy, Contact and Schema text, and added the IP suggestion and two helper routes; built by Irteza Raza and Abdur Rauf with Claude from Hassan Majid's interface ideas, and listed in `CHANGELOG.md`. Version 20 (12 Nov 2026) added the QR label and scanner bonus feature and moved the repository to `AbdurRauf-01/ef101-fall2026-p11`; built by Abdur Rauf with Claude. A final review on 8 Nov 2026, also with Claude, found and fixed further errors. Every member reviewed, tested and can explain the project.

**Who did what** (same as report section 9):

| Member | Main area | Contribution |
| --- | --- | --- |
| Irteza Raza (EE-26129) | Database: `schema.sql`, `db.py`, `queries.py`, `seed.py`, `inventory.db` | Built the database files using Claude. Fixed IP address handling, current-fault editing, maintenance history management and the Fault History table using Claude. Added the GPU VRAM field and the Delete and Edit buttons in maintenance history using Claude. Built the v19 interface from Hassan Majid's ideas using Claude. |
| Abdur Rauf (EE-26138) | Backend: `app.py`, `qr_labels.py`, `test_app.py`, `migrate.py`, launcher scripts, README | Built these files and the interface using Claude. Fixed the major asset editing error (see the report, section 5), cost logic, dates, asset IDs, RAM types, dashboard sorting, the asset editing page and unused code using Claude. Added the theme, sidebar, Credits, Privacy Policy, Contact, Fault History and Current fault field using Claude. Built the v19 interface from Hassan Majid's ideas using Claude. Added the v20 QR labels, label sheet, scanner page and short-link routes (`qr_labels.py`, `static/scan.js`) using Claude. |
| Hassan Majid (EE-26125) | Frontend design (ideas); final report | Proposed the interface design ideas: theme, sidebar, sidebar sections and assets list sorting. Ideas only, no code; Irteza Raza and Abdur Rauf built them in v19. Answers the frontend viva questions. |

## Limitations

No login or user roles; data entry is manual; SQLite suits one site and few concurrent users; demo data is synthetic.
