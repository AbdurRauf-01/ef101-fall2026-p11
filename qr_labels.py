"""QR asset labels (added in version 20). No database access and no Flask here: this file only
(1) builds the text stored in a label's QR code, (2) turns text into a QR code (SVG) and
(3) works out which asset ID a scanned text means.

A label's QR code holds a short plain-text block with the asset's specs, for example

    EF101-ASSET
    ID: L1-PC-004
    Model: HP ProDesk 400 G7
    CPU: Intel Core i3-10100
    RAM: 4 GB DDR4 | Storage: HDD 500 GB
    GPU: Integrated only | OS: Windows 10 Pro
    IP: 192.168.1.4 | Location: Lab 1
    Warranty to: 2028-12-29
    Status: Operational (as of 2026-11-12)

 * Any phone camera shows this text with no network and no access to this computer, so the specs can be
   read from the label even though the app runs only on 127.0.0.1.
 * The text is a snapshot. The "as of" date says when the label was made; if a spec or the status changed
   afterwards, the printed code is out of date until it is printed again. The asset page in this app is
   always current: the Scan page reads the code with the camera and only uses the ID line to open it.
 * Older codes still work: a link (.../a/L1-PC-001), 'EF101-ASSET:L1-PC-001' and a bare ID are understood too.
The code is read as plain text, so USB barcode scanners (they type the text like a keyboard) work too.
"""
import io
import re
from urllib.parse import quote, unquote, urlsplit

try:                                    # segno is a small pure-Python package listed in requirements.txt
    import segno
except ImportError:                     # the app still starts without it; the QR pages then say what to install
    segno = None

TEXT_PREFIX = "EF101-ASSET:"            # a label that holds only "EF101-ASSET:L1-PC-001" is understood as well
BLOCK_HEADER = "EF101-ASSET"            # first line of the spec block
FIELD_MAX = 60                          # each field is cut to this many characters so the code stays easy to scan
MAX_CODE = 1000                         # a scanned text longer than this is ignored (a full spec block is under 700)
MAX_ID = 40                             # longest asset ID the app accepts
_PATH_RE = re.compile(r"^/(?:a|assets)/([^/?#]+)")
_BLOCK_ID_RE = re.compile(r"^EF101-ASSET\b[^A-Za-z0-9]*?\bID:\s*([A-Za-z0-9._-]{1,%d})(?=\s|$)" % MAX_ID, re.I)


def available():
    return segno is not None


def asset_link(host_url, asset_id):
    """The text stored in the QR code: link to the short lookup route, e.g. http://127.0.0.1:5000/a/L1-PC-001."""
    return f"{host_url.rstrip('/')}/a/{quote(asset_id, safe='')}"


def _clean(value, limit=None):
    """One line of plain text: whitespace (including line breaks) collapsed, cut to `limit` characters.
    The default is looked up when the function runs (not when the module loads), so changing FIELD_MAX works."""
    limit = FIELD_MAX if limit is None else limit
    text = " ".join(str(value if value is not None else "").split())
    return text[:limit].rstrip()


def spec_text(asset, as_of):
    """The text stored in a label's QR code: the asset's specs, its status and the date the label was made.
    `asset` is a database row (or dict) from the assets table; `as_of` is an ISO date such as 2026-11-12."""
    get = lambda key: asset[key] if key in asset.keys() else None          # works for sqlite3.Row and dict
    ram = f"{_clean(get('ram_gb'))} GB {_clean(get('ram_type'))}".strip()
    storage = f"{_clean(get('storage_type'))} {_clean(get('storage_gb'))} GB".strip()
    gpu = _clean(get("gpu")) or "Integrated only"
    if _clean(get("gpu")) and get("gpu_vram_gb"):
        gpu = _clean(f"{_clean(get('gpu'), FIELD_MAX - 8)} {_clean(get('gpu_vram_gb'))} GB")
    model = _clean(f"{_clean(get('manufacturer'), 20)} {_clean(get('model'), 40)}")
    status = _clean(get("status")) or "Unknown"
    if not get("active") and get("active") is not None:
        status = f"Retired, last {status}"
    lines = [
        BLOCK_HEADER,
        f"ID: {_clean(get('asset_id'), MAX_ID)}",
        f"Model: {model}",
        f"CPU: {_clean(get('cpu'))}",
        f"RAM: {ram} | Storage: {storage}",
        f"GPU: {gpu} | OS: {_clean(get('os'))}",
        f"IP: {_clean(get('ip_address')) or 'Not Assigned'} | Location: {_clean(get('location'))}",
        f"Warranty to: {_clean(get('warranty_expiry'))}",
        f"Status: {status} (as of {_clean(as_of, 10)})",
    ]
    return "\n".join(lines)


def qr_svg(text, scale=4, border=4, standalone=False):
    """SVG markup of a QR code for `text` (error correction Q: about a quarter of the code may be damaged;
    border 4 modules is the quiet zone the QR standard asks for, and scanners read it more reliably).
    standalone=False -> markup for placing inside an HTML page (no size, scales with its container).
    standalone=True  -> a complete .svg file with xmlns and a fixed size."""
    if segno is None:
        raise RuntimeError("The 'segno' package is not installed. Run: pip install -r requirements.txt")
    code = segno.make(text, error="q", boost_error=False)       # fixed level: the same input gives the same code
    buf = io.BytesIO()
    if standalone:
        code.save(buf, kind="svg", scale=scale, border=border, xmldecl=True, svgns=True, nl=True,
                  dark="#000000", light="#ffffff")
    else:
        code.save(buf, kind="svg", scale=scale, border=border, xmldecl=False, svgns=False, omitsize=True,
                  nl=False, dark="#000000", light="#ffffff")
    return buf.getvalue().decode("utf-8")


def code_to_asset_id(text):
    """The asset ID a scanned or typed text stands for, or None.
    Understood: the spec block ('EF101-ASSET' then 'ID: ...'; line breaks may be missing when the text was
    pasted into a one-line box), a link (.../a/ID or .../assets/ID), 'EF101-ASSET:ID', or the bare ID itself.
    The result is only a candidate; the caller still checks that such an asset exists."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text or len(text) > MAX_CODE:
        return None
    m = _BLOCK_ID_RE.match(text)
    if m:
        return m.group(1)
    if text.upper().startswith(TEXT_PREFIX):
        text = text[len(TEXT_PREFIX):].strip()
    elif "://" in text or text.startswith("/"):
        try:
            path = urlsplit(text).path
        except ValueError:
            return None
        m = _PATH_RE.match(path)
        if not m:
            return None
        text = unquote(m.group(1))
    if not text or len(text) > MAX_ID or any(c.isspace() for c in text):
        return None
    return text
