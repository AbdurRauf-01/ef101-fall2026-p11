#!/usr/bin/env bash
# macOS / Fedora / Ubuntu bootstrap. Usage: bootstrap.sh start|reset|test
# Makes sure a usable Python 3.8+ exists, then hands over to launcher.py (which checks Flask, segno ... and shows its
# own menu). If Python is missing, a menu asks first: 1 install automatically (default), 2 install it yourself
# (official links shown), 3 continue anyway, 4 exit. Nothing is installed without that choice.
set -u

ACTION="${1:-start}"
EXTRA=("${@:2}")      # extra options for launcher.py, e.g. --no-install, --demo, --empty, --yes
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
cd "$ROOT" || exit 1

PYTHON_ORG_VERSION="3.12.10"   # used only for the macOS fallback installer when Homebrew is absent
OS="$(uname -s)"

say() { printf '%s\n' "$*"; }

finish() {  # $1 = exit code; keep the window open when it was opened by a double-click
    if [ "${LAUNCHER_PAUSE:-}" = "1" ]; then
        printf '\nPress Enter to close this window... '
        read -r _ || true
    fi
    exit "$1"
}

relaunch_in_terminal() {
    # Linux file managers often run .sh files with no terminal. Reopen ourselves inside one.
    [ "$OS" = "Linux" ] || return 0
    if [ -t 0 ] || [ -t 1 ]; then return 0; fi          # already in a terminal (or being piped on purpose)
    [ -n "${LAUNCHER_IN_TERMINAL:-}" ] && return 0
    [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || return 0   # no graphical session
    local e=(env LAUNCHER_IN_TERMINAL=1 LAUNCHER_PAUSE=1)
    local self=(bash "$HERE/bootstrap.sh" "$ACTION" ${EXTRA[@]+"${EXTRA[@]}"})   # run through bash: bootstrap.sh itself needs no chmod +x
    if command -v x-terminal-emulator >/dev/null 2>&1; then exec "${e[@]}" x-terminal-emulator -e "${self[@]}"; fi
    if command -v gnome-terminal >/dev/null 2>&1; then exec "${e[@]}" gnome-terminal -- "${self[@]}"; fi
    if command -v konsole >/dev/null 2>&1; then exec "${e[@]}" konsole -e "${self[@]}"; fi
    if command -v xfce4-terminal >/dev/null 2>&1; then exec "${e[@]}" xfce4-terminal -x "${self[@]}"; fi
    if command -v kitty >/dev/null 2>&1; then exec "${e[@]}" kitty "${self[@]}"; fi
    if command -v xterm >/dev/null 2>&1; then exec "${e[@]}" xterm -e "${self[@]}"; fi
    return 0   # no terminal found: carry on without one
}

py_ok() {  # $1 = python command/path: exists and is 3.8+
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' >/dev/null 2>&1
}

venv_capable() {  # $1 = python: can really build a venv with pip (Ubuntu/Debian ship it as a separate package)
    local tmp
    tmp="$(mktemp -d 2>/dev/null)" || return 1
    "$1" -m venv "$tmp/v" >/dev/null 2>&1
    local rc=$?
    rm -rf "$tmp"
    return $rc
}

has_packages() {  # $1 = python: Flask and segno are already installed (system-wide), so no venv is needed
    "$1" -c 'import flask, segno' >/dev/null 2>&1
}

find_python() {
    PY=""
    local candidates=()
    if [ "$OS" = "Darwin" ]; then
        candidates+=(/opt/homebrew/bin/python3 /usr/local/bin/python3
                     /Library/Frameworks/Python.framework/Versions/Current/bin/python3)
        # /usr/bin/python3 is a stub that pops up an install dialog unless the Command Line Tools exist.
        if xcode-select -p >/dev/null 2>&1; then candidates+=(/usr/bin/python3); fi
    fi
    local c
    for c in python3 python; do
        if command -v "$c" >/dev/null 2>&1; then candidates+=("$(command -v "$c")"); fi
    done
    # 1st choice: a Python that already has everything (installed system-wide) - no venv needed.
    for c in "${candidates[@]}"; do
        [ "$OS" = "Darwin" ] && [ "$c" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1 && continue
        if [ -x "$c" ] && py_ok "$c" && has_packages "$c"; then PY="$c"; return 0; fi
    done
    # 2nd choice: any Python 3.8+ that can build a venv (the launcher then offers to install the packages into it).
    for c in "${candidates[@]}"; do
        [ "$OS" = "Darwin" ] && [ "$c" = "/usr/bin/python3" ] && ! xcode-select -p >/dev/null 2>&1 && continue
        if [ -x "$c" ] && py_ok "$c" && venv_capable "$c"; then PY="$c"; return 0; fi
    done
    return 1
}

as_root() {
    if [ "$(id -u)" -eq 0 ]; then "$@"; else sudo "$@"; fi
}

install_python_macos() {
    local brew=""
    for b in brew /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if command -v "$b" >/dev/null 2>&1; then brew="$(command -v "$b")"; break; fi
    done
    if [ -n "$brew" ]; then
        say "Installing Python with Homebrew ..."
        "$brew" install python && return 0
        say "Homebrew install failed; trying the python.org installer instead."
    fi
    local pkg
    pkg="$(mktemp -d)/python-${PYTHON_ORG_VERSION}-macos11.pkg" || return 1
    local url="https://www.python.org/ftp/python/${PYTHON_ORG_VERSION}/python-${PYTHON_ORG_VERSION}-macos11.pkg"
    say "Downloading Python ${PYTHON_ORG_VERSION} from python.org ..."
    curl -fL --proto '=https' --tlsv1.2 -o "$pkg" "$url" || return 1
    if ! pkgutil --check-signature "$pkg" 2>/dev/null | grep -q "Python Software Foundation"; then
        say "The downloaded installer is not signed by the Python Software Foundation. Aborting."
        rm -f "$pkg"
        return 1
    fi
    say "Installing (macOS will ask for your password) ..."
    sudo installer -pkg "$pkg" -target / || { rm -f "$pkg"; return 1; }
    rm -f "$pkg"
}

install_python_linux() {
    local id="" like=""
    if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        id="${ID:-}"; like="${ID_LIKE:-}"
    fi
    case " $id $like " in
        *" fedora "*|*" rhel "*|*" centos "*)
            say "Installing Python with dnf (may ask for your password) ..."
            as_root dnf install -y python3 python3-pip ;;
        *" ubuntu "*|*" debian "*)
            say "Installing Python with apt (may ask for your password) ..."
            as_root apt-get update && as_root apt-get install -y python3 python3-venv python3-pip ;;
        *)
            say "Unsupported Linux distribution (${id:-unknown}). Install python3, python3-venv and python3-pip, then run again."
            return 1 ;;
    esac
}

python_menu() {
    # Python 3.8+ is missing: ask before installing anything.
    local preset="${LAUNCHER_CHOICE:-}" choice ans
    while true; do
        say ""
        say "A usable Python 3.8+ (with venv and pip) was not found."
        say "Official source: https://www.python.org/downloads/"
        say ""
        say "  1. Install Python automatically (default; needs internet; the packages then go into venv/)"
        say "  2. Install Python yourself, system-wide (shows the official links first)"
        say "  3. Continue anyway (may stop with an error)"
        say "  4. Exit"
        if [ -n "$preset" ]; then choice="$preset"; say "Choice $choice (preset)."; preset=""
        else
            printf 'Choose 1-4 [1]: '
            if ! read -r choice; then
                say ""; say "No keyboard input, so nothing was installed. Run again in a terminal, or set LAUNCHER_CHOICE=1."
                finish 0
            fi
            [ -z "$choice" ] && choice=1
        fi
        case "$choice" in
            1)
                say ""
                if [ "$OS" = "Darwin" ]; then install_python_macos; else install_python_linux; fi
                hash -r
                if find_python; then export LAUNCHER_CHOICE=1; return 0; fi
                say ""; say "Python is still not usable after the install attempt." ;;
            2)
                say ""
                say "Install Python yourself. Download only from the official site: https://www.python.org/downloads/"
                case "$OS" in
                    Darwin) say "  macOS: the python.org installer, or Homebrew (https://brew.sh): brew install python" ;;
                    *)      say "  Fedora:        sudo dnf install python3 python3-pip"
                            say "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip" ;;
                esac
                say "  Safer this way: this script runs nothing with administrator rights and downloads nothing."
                say "  Then run this script again, or answer Y below."
                printf 'Done installing? Y = check again and launch, N = back to the menu [Y/N]: '
                if read -r ans && [ "${ans#[Yy]}" != "$ans" ]; then
                    hash -r
                    if find_python; then return 0; fi
                    say ""; say "Checked again: Python 3.8+ was not found."
                fi ;;
            3)
                say ""; say "Nothing can run without Python 3.8+. Pick 1 or 2, or 4 to exit." ;;
            4)
                say "Exited. Nothing was installed."; finish 0 ;;
        esac
    done
}

relaunch_in_terminal

# Fast path: a working venv already exists, so no system Python checks are needed.
VENV_PY="$ROOT/venv/bin/python"
if [ -x "$VENV_PY" ] && "$VENV_PY" -c 'import sys' >/dev/null 2>&1; then
    PY="$VENV_PY"
else
    if ! find_python; then python_menu; fi
fi

"$PY" "$HERE/launcher.py" "$ACTION" ${EXTRA[@]+"${EXTRA[@]}"}
finish $?
