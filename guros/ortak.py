"""Shared helpers for every GurOS script: paths, settings, Turkish-aware text folding, safe writes.

Only the Python standard library is used, on purpose: a dependency is the thing that quietly breaks
three months later.
"""
import datetime as _dt
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

SURUM = "1.1.0"
KOD = Path(__file__).resolve().parent            # <vault>/.claude/guros
VARSAYILAN = {
    "ad": "Kullanıcı",
    "asistan": "Logos",
    "hafiza_klasoru": "🔮 Logos",
    "proje_klasoru": "Projeler",
    "ozel_klasorler": ["🔒 Özel"],
    "hatirlatma_esigi": 10,
    "recall_sonuc": 3,
    "baglam_siniri": 6000,
}

for _akis in (sys.stdout, sys.stderr):
    try:
        if _akis is not None and hasattr(_akis, "reconfigure"):
            _akis.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass


def vault_kok():
    """The vault root: GUROS_VAULT if set, else two levels above this file (<vault>/.claude/guros)."""
    env = os.environ.get("GUROS_VAULT")
    return Path(env).resolve() if env else KOD.parents[1]


def ayarlar(vault=None):
    vault = Path(vault) if vault else vault_kok()
    veri = dict(VARSAYILAN)
    try:
        with io.open(vault / ".claude" / "guros" / "ayarlar.json", encoding="utf-8") as f:
            veri.update(json.load(f))
    except (OSError, ValueError):
        pass
    return veri


def hafiza_dizini(vault=None, ay=None):
    vault = Path(vault) if vault else vault_kok()
    ay = ay or ayarlar(vault)
    return vault / ay["hafiza_klasoru"]


def durum_dizini(vault=None):
    """Machine-local state (index, counters). Kept outside the vault so sync tools never churn on it."""
    vault = (Path(vault) if vault else vault_kok()).resolve()
    taban = os.environ.get("GUROS_STATE") or os.path.join(os.path.expanduser("~"), ".guros")
    ad = re.sub(r"[^A-Za-z0-9]+", "-", vault.name).strip("-")[:30] or "vault"
    iz = hashlib.sha1(str(vault).lower().encode("utf-8")).hexdigest()[:8]
    yol = Path(taban) / f"{ad}-{iz}"
    yol.mkdir(parents=True, exist_ok=True)
    return yol


_KATLA = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def katla(metin):
    """Lower-case and fold Turkish letters so 'İstanbul', 'istanbul' and 'ISTANBUL' compare equal."""
    metin = unicodedata.normalize("NFKC", metin or "").replace("İ", "i")
    return metin.casefold().replace("̇", "").translate(_KATLA)


def bugun():
    return _dt.date.today().isoformat()


def simdi():
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def oku(yol, varsayilan=""):
    try:
        with io.open(yol, encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, UnicodeError):
        return varsayilan


def guvenli_yaz(yol, metin):
    """Write through a temp file and os.replace, so a failure never leaves a truncated note behind."""
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    veri = metin.encode("utf-8")          # encode first: an encoding error must happen before anything is touched
    fd, gecici = tempfile.mkstemp(prefix=".guros-", dir=str(yol.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(veri)
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def ekle(yol, satir):
    """Append one line (never rewrite) — notes may be open in Obsidian or syncing at the same moment."""
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    onceki = oku(yol)
    with io.open(yol, "a", encoding="utf-8", newline="\n") as f:
        if onceki and not onceki.endswith("\n"):
            f.write("\n")
        f.write(satir.rstrip("\n") + "\n")


def sade(metin):
    """Folded text with every non-alphanumeric run turned into one space: '🔒 Özel_Alan/' -> 'ozel alan'."""
    metin = re.sub(r"%20", " ", metin or "")
    return " ".join(re.split(r"[^a-z0-9]+", katla(metin))).strip()


def ozel_anilir(metin, ay=None):
    """True if the text names a private folder anywhere (spacing, quoting and emoji differences ignored)."""
    ay = ay or ayarlar()
    duz = f" {sade(metin)} "
    for klasor in ay.get("ozel_klasorler", []):
        isaret = sade(Path(klasor).name)
        if isaret and f" {isaret} " in duz:
            return klasor
    return None


def ozel_mi(goreli, ay=None):
    """True if a vault-relative path sits inside one of the private folders."""
    ay = ay or ayarlar()
    parcalar = [katla(p) for p in Path(goreli).parts]
    for klasor in ay.get("ozel_klasorler", []):
        hedef = [katla(p) for p in Path(klasor).parts]
        if hedef and parcalar[: len(hedef)] == hedef:
            return True
    return False


def hook_girdisi():
    """Claude Code passes hook data as JSON on stdin; an empty or broken payload is treated as {}."""
    try:
        # bytes, not text: on Windows the text layer would decode Claude Code's UTF-8 with the ANSI code page,
        # and a private folder named "🔒 Özel Alan" would arrive as mojibake and slip past the guard
        ham = sys.stdin.buffer.read() if hasattr(sys.stdin, "buffer") else sys.stdin.read().encode("utf-8")
        veri = ham.decode("utf-8-sig", errors="replace")
    except (OSError, ValueError, AttributeError):
        return {}
    try:
        return json.loads(veri) if veri.strip() else {}
    except ValueError:
        return {}


def hook_baglami(olay, metin):
    """Print additional context the way Claude Code expects it from SessionStart / UserPromptSubmit hooks."""
    if metin:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": olay, "additionalContext": metin}}, ensure_ascii=False))
