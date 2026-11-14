"""CPU families and CPU models for the Add / Edit form, and the check that a CPU belongs to its family.

How it works (version 23):
  * FAMILIES is the finite list of CPU families the form offers (desktop and laptop, Intel, AMD, Apple, Qualcomm).
  * CPU_MODELS is a list of common models, used only as suggestions while typing. Any other model may be typed.
  * family_for_cpu() reads the family out of a CPU name with pattern rules (for example "Core i5-12400" is
    "Core i5", "Ryzen 7 5700G" is "Ryzen 7"). Because it is pattern based, models released later still match.
  * check_cpu_family() is what validate_asset() calls. A recognised CPU must be given its own family. A CPU the
    rules do not recognise must use the family "Other", because nothing can be checked for it.
No database change: the two values are still stored as text in assets.cpu and assets.cpu_family.
"""
import re

OTHER = "Other"

FAMILIES = [
    # Intel, current naming
    "Core Ultra 9", "Core Ultra 7", "Core Ultra 5", "Core Ultra 3",
    "Core 7", "Core 5", "Core 3",
    # Intel Core, 2008 onwards (desktop and laptop)
    "Core i9", "Core i7", "Core i5", "Core i3",
    # Intel older and entry level
    "Core 2 Quad", "Core 2 Duo", "Core Duo", "Pentium", "Celeron", "Atom", "Intel N-series", "Xeon",
    # AMD Ryzen
    "Ryzen AI 9", "Ryzen AI 7", "Ryzen AI 5", "Ryzen 9", "Ryzen 7", "Ryzen 5", "Ryzen 3",
    "Threadripper", "EPYC",
    # AMD older and entry level
    "Athlon", "Sempron", "Phenom", "FX", "A-Series",
    # Apple and Qualcomm (laptops)
    "Apple M5", "Apple M4", "Apple M3", "Apple M2", "Apple M1", "Snapdragon X",
    OTHER,
]

# (pattern, family) in order: the first rule that matches wins, so more specific rules come first.
_RULES = [
    (r"\bCore\s*Ultra\s*([3579])\b", "Core Ultra {0}"),
    (r"\bCore\s*i([3579])\b", "Core i{0}"),
    (r"(?<![A-Za-z0-9])i([3579])[-\s]?\d{3,5}", "Core i{0}"),           # "i5-12400" typed without "Core"
    (r"\bCore\s*([357])\s+\d{3}", "Core {0}"),                            # Core 5 120U (2024 naming)
    (r"\bCore\s*2\s*Quad\b", "Core 2 Quad"),
    (r"\bCore\s*2\s*Duo\b", "Core 2 Duo"),
    (r"\bCore\s*Duo\b", "Core Duo"),
    (r"\bPentium\b", "Pentium"),
    (r"\bCeleron\b", "Celeron"),
    (r"\bAtom\b", "Atom"),
    (r"\bXeon\b", "Xeon"),
    (r"(?:\bIntel\s+(?:Processor\s+)?|^)N(?:95|97|100|150|200|305|355)\b", "Intel N-series"),
    (r"\bThreadripper\b", "Threadripper"),
    (r"\bRyzen\s*AI\s*([3579])\b", "Ryzen AI {0}"),
    (r"\bRyzen\s*([3579])\b", "Ryzen {0}"),
    (r"\bEPYC\b", "EPYC"),
    (r"\bAthlon\b", "Athlon"),
    (r"\bSempron\b", "Sempron"),
    (r"\bPhenom\b", "Phenom"),
    (r"\bFX[-\s]?\d{4}", "FX"),
    (r"\bA(?:4|6|8|10|12)-\d{4}", "A-Series"),
    (r"^(?:Apple\s+)?M(\d{1,2})\b", "Apple M{0}"),
    (r"\bSnapdragon\s*X\b", "Snapdragon X"),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), f) for p, f in _RULES]


def _clean(text):
    text = (text or "").replace("(R)", "").replace("(r)", "").replace("(TM)", "").replace("(tm)", "")
    text = text.replace("®", "").replace("™", "")
    return re.sub(r"\s+", " ", text).strip()


def family_for_cpu(cpu):
    """The family of a CPU name, or None when no rule recognises it."""
    text = _clean(cpu)
    for rx, fam in _COMPILED:
        m = rx.search(text)
        if m:
            return fam.format(*m.groups())
    return None


def _key(text):
    return re.sub(r"\s+", "", (text or "")).lower()


def check_cpu_family(cpu, family):
    """Returns (canonical_family, error). error is None when the pair is fine; canonical_family is the family
    spelled the way the catalog spells it (so 'core i5' is stored as 'Core i5')."""
    cpu, family = _clean(cpu), _clean(family)
    expected = family_for_cpu(cpu)
    if expected is None:
        if _key(family) == _key(OTHER):
            return OTHER, None
        return family, (f"CPU '{cpu}' is not recognised, so its family cannot be checked. "
                        f"Pick a model from the list, or choose the family '{OTHER}'.")
    if _key(family) == _key(expected):
        return expected, None
    return family, (f"CPU '{cpu}' belongs to the family '{expected}', not '{family}'. "
                    f"Change the family to '{expected}' or correct the CPU.")


def _models():
    out = []
    intel = {
        "Core i3": ["i3-6100", "i3-7100", "i3-8100", "i3-9100", "i3-10100", "i3-10105", "i3-12100", "i3-13100",
                    "i3-8130U", "i3-1115G4", "i3-1215U", "i3-1315U"],
        "Core i5": ["i5-6500", "i5-6600", "i5-7400", "i5-7500", "i5-8400", "i5-8500", "i5-9400", "i5-9400F",
                    "i5-9600K", "i5-10400", "i5-10400F", "i5-10500", "i5-10505", "i5-11400", "i5-11400F",
                    "i5-12400", "i5-12400F", "i5-12500", "i5-12600K", "i5-13400", "i5-13400F", "i5-13500",
                    "i5-13600K", "i5-14400", "i5-14400F", "i5-14500", "i5-14600K",
                    "i5-8250U", "i5-8265U", "i5-9300H", "i5-10210U", "i5-10300H", "i5-1035G1", "i5-1135G7",
                    "i5-1145G7", "i5-11300H", "i5-1235U", "i5-1240P", "i5-12500H", "i5-1335U", "i5-1345U",
                    "i5-13500H"],
        "Core i7": ["i7-6700", "i7-7700", "i7-8700", "i7-9700", "i7-10700", "i7-11700", "i7-12700", "i7-12700K",
                    "i7-13700", "i7-13700K", "i7-14700", "i7-14700K",
                    "i7-8550U", "i7-8565U", "i7-8750H", "i7-9750H", "i7-10510U", "i7-10750H", "i7-1065G7",
                    "i7-1165G7", "i7-1185G7", "i7-11800H", "i7-1255U", "i7-1260P", "i7-12700H", "i7-1355U",
                    "i7-1365U", "i7-13700H"],
        "Core i9": ["i9-9900K", "i9-10900", "i9-10900K", "i9-11900K", "i9-12900K", "i9-13900K", "i9-14900K",
                    "i9-12900H", "i9-13900H"],
    }
    for names in intel.values():
        out += ["Intel Core " + n for n in names]
    out += ["Intel Core Ultra " + n for n in ["5 125H", "7 155H", "7 165H", "9 185H", "5 125U", "7 165U",
                                              "5 245K", "7 265K", "9 285K", "7 258V", "9 288V"]]
    out += ["Intel Core " + n for n in ["3 100U", "5 120U", "7 150U"]]
    out += ["Intel Core 2 Duo E6550", "Intel Core 2 Duo E7500", "Intel Core 2 Duo E8400",
            "Intel Core 2 Quad Q6600", "Intel Core 2 Quad Q9400", "Intel Core Duo T2400",
            "Intel Pentium G4560", "Intel Pentium Gold G5400", "Intel Pentium Gold G6400", "Intel Pentium Silver N5000",
            "Intel Celeron G3900", "Intel Celeron G4900", "Intel Celeron G5905", "Intel Celeron G6900",
            "Intel Celeron N4020", "Intel Celeron N4500",
            "Intel N95", "Intel N100", "Intel N200", "Intel N305",
            "Intel Xeon E-2124G", "Intel Xeon E3-1230 v5", "Intel Xeon E5-2680 v4", "Intel Xeon W-2245"]
    amd = {
        "3": ["3100", "3200G", "4100", "5300G", "5425U", "7330U"],
        "5": ["1600", "2600", "3400G", "3500", "3600", "4500", "5500", "5600", "5600G", "5600X", "7500F", "7600",
              "7600X", "8600G", "9600X", "3500U", "4500U", "5500U", "5600H", "5600U", "5625U", "6600H", "7520U",
              "7535HS", "7640HS", "7640U", "PRO 5650U"],
        "7": ["1700", "2700", "3700X", "5700G", "5700X", "5800X", "5800X3D", "7700", "7700X", "7800X3D", "8700G",
              "9700X", "9800X3D", "4700U", "5700U", "5800H", "5800U", "6800H", "7730U", "7735HS", "7840HS",
              "7840U", "8845HS"],
        "9": ["3900X", "5900X", "5950X", "7900", "7900X", "7950X", "7950X3D", "9900X", "9950X", "5900HX", "6900HX",
              "7845HX", "7940HS", "7945HX"],
    }
    for n, names in amd.items():
        out += [f"AMD Ryzen {n} {s}" for s in names]
    out += ["AMD Ryzen AI 9 HX 370", "AMD Ryzen AI 9 365", "AMD Ryzen AI 7 350", "AMD Ryzen AI 5 340",
            "AMD Ryzen Threadripper 1950X", "AMD Ryzen Threadripper 3970X", "AMD Ryzen Threadripper PRO 5975WX",
            "AMD EPYC 7402P",
            "AMD Athlon 200GE", "AMD Athlon 3000G", "AMD Athlon II X4 640", "AMD Sempron 145",
            "AMD Phenom II X4 955", "AMD FX-6300", "AMD FX-8350",
            "AMD A6-9500", "AMD A8-7600", "AMD A10-7850K", "AMD A10-9700"]
    for gen in ("M1", "M2", "M3"):
        out += [f"Apple {gen}", f"Apple {gen} Pro", f"Apple {gen} Max"]
    out += ["Apple M1 Ultra", "Apple M2 Ultra", "Apple M3 Ultra", "Apple M4", "Apple M4 Pro", "Apple M4 Max", "Apple M5",
            "Snapdragon X Elite X1E-80-100", "Snapdragon X Plus X1P-64-100", "Snapdragon X X1-26-100"]
    return out


CPU_MODELS = _models()
