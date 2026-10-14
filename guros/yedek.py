"""Optional backup: commit the vault to a PRIVATE git repository, with a secret gate in front of every commit.

    python yedek.py --kur https://github.com/<kullanici>/<ozel-repo>.git    # one-time setup
    python yedek.py                                                         # commit + push now
    python yedek.py --durum

Rules built into the code:
  * private folders are written into .gitignore and never committed;
  * every staged change is scanned for things that look like keys, tokens or passwords; one hit = no commit;
  * no force push, ever. If the remote moved on, the user decides.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

SIR_DESENLERI = [
    ("OpenAI/Anthropic anahtarı", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("Google API anahtarı", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("AWS erişim anahtarı", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_\-]{33}\b")),
    ("özel anahtar bloğu", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("parola ataması", re.compile(r"(?i)\b(password|parola|şifre|sifre|passwd|secret|api[_-]?key)\s*[:=]\s*\S{6,}")),
]
GITIGNORE_SABIT = [".obsidian/workspace*.json", ".trash/", ".DS_Store", "Thumbs.db", "__pycache__/", ".claude/settings.local.json"]


def _git(*args, vault=None, check=True):
    # core.quotepath=false: otherwise non-ASCII paths come back octal-escaped and no path check can match them
    return subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(vault or ortak.vault_kok()), *args],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=check, timeout=120)


def _gitignore(vault, ay):
    yol = vault / ".gitignore"
    mevcut = ortak.oku(yol).splitlines()
    gerek = GITIGNORE_SABIT + [k.rstrip("/") + "/" for k in ay.get("ozel_klasorler", [])]
    eksik = [g for g in gerek if g not in mevcut]
    if eksik:
        ortak.ekle(yol, "# GurOS: özel alanlar ve geçici dosyalar yedeğe girmez\n" + "\n".join(eksik))


def izlenen_ozel(vault, ay):
    """Files of a private folder that git tracks (staged now, or committed before the folder became private)."""
    return [d for d in _git("ls-files", vault=vault).stdout.splitlines() if ortak.ozel_mi(d, ay)]


def _ozel_uyarisi(dosyalar, ay):
    print(f"Özel alandaki {len(dosyalar)} dosya git'te izleniyor. Diskten silmeden izlemeden çıkarmak için:", file=sys.stderr)
    for k in ay.get("ozel_klasorler", []):
        print(f'  git rm -r --cached "{k}"', file=sys.stderr)
    print("Daha önce gönderildiyse uzak depodaki geçmişte de durur; depo özel olmalı.", file=sys.stderr)


def kur(uzak):
    if not shutil.which("git"):
        raise SystemExit("git bulunamadı. Önce Git'i kur (https://git-scm.com).")
    vault, ay = ortak.vault_kok(), ortak.ayarlar()
    if not (vault / ".git").exists():
        _git("init", "-b", "main", vault=vault)
    _gitignore(vault, ay)
    uzaklar = _git("remote", vault=vault).stdout.split()
    if "origin" in uzaklar:
        _git("remote", "set-url", "origin", uzak, vault=vault)
    else:
        _git("remote", "add", "origin", uzak, vault=vault)
    print("Yedek deposu ayarlandı. ÖNEMLİ: GitHub'daki depo PRIVATE (özel) olmalı; notların herkese açık olmasın.")
    izlenen = izlenen_ozel(vault, ay)
    if izlenen:
        _ozel_uyarisi(izlenen, ay)


def tara(vault):
    """Return [(file, kind)] for staged additions that look like secrets."""
    fark = _git("diff", "--cached", "-U0", "--no-color", vault=vault).stdout
    bulgu, dosya = [], ""
    for satir in fark.splitlines():
        if satir.startswith("+++ b/"):
            dosya = satir[6:]
        elif satir.startswith("+") and not satir.startswith("+++"):
            for tur, desen in SIR_DESENLERI:
                if desen.search(satir):
                    bulgu.append((dosya, tur))
    return sorted(set(bulgu))


def yedekle(sessiz=False):
    vault, ay = ortak.vault_kok(), ortak.ayarlar()
    if not (vault / ".git").exists():
        if not sessiz:
            print("Yedek kurulmamış. Kurmak için: yedek.py --kur <özel-repo-adresi>")
        return 0
    _gitignore(vault, ay)
    _git("add", "-A", vault=vault)
    izlenen = izlenen_ozel(vault, ay)
    if izlenen:
        _git("reset", "-q", vault=vault, check=False)
        print("Yedek DURDU: hiçbir şey commit edilmedi.", file=sys.stderr)
        _ozel_uyarisi(izlenen, ay)
        return 2
    bulgu = tara(vault)
    if bulgu:
        _git("reset", "-q", vault=vault, check=False)
        print("Yedek DURDU: sır gibi görünen satırlar var, hiçbir şey commit edilmedi:", file=sys.stderr)
        for dosya, tur in bulgu:
            print(f"  - {dosya}: {tur}", file=sys.stderr)
        print("Sırrı nottan çıkar (bir parola yöneticisine taşı) ve yeniden dene.", file=sys.stderr)
        return 2
    if not _git("diff", "--cached", "--name-only", vault=vault).stdout.strip():
        if not sessiz:
            print("Değişiklik yok; yedek güncel.")
        return 0
    sayi = len(_git("diff", "--cached", "--name-only", vault=vault).stdout.splitlines())
    _git("-c", "user.name=GurOS", "-c", "user.email=guros@localhost", "commit", "-q", "-m",
         f"otomatik yedek: {sayi} dosya — {ortak.simdi()}", vault=vault)
    itme = _git("push", "-q", "origin", "HEAD", vault=vault, check=False)
    if itme.returncode != 0:
        print("Commit yapıldı ama gönderilemedi (ağ ya da yetki): " + (itme.stderr.strip().splitlines() or [""])[-1], file=sys.stderr)
        return 1
    if not sessiz:
        print(f"Yedeklendi: {sayi} dosya.")
    return 0


def durum():
    vault = ortak.vault_kok()
    if not (vault / ".git").exists():
        print("Yedek kurulu değil.")
        return
    uzak = _git("remote", "get-url", "origin", vault=vault, check=False).stdout.strip() or "—"
    son = _git("log", "-1", "--format=%cd · %s", "--date=format:%Y-%m-%d %H:%M", vault=vault, check=False).stdout.strip() or "henüz commit yok"
    print(f"Uzak depo: {uzak}\nSon yedek: {son}")


def main(argv):
    ap = argparse.ArgumentParser(description="GurOS yedek (isteğe bağlı)")
    ap.add_argument("--kur")
    ap.add_argument("--durum", action="store_true")
    ap.add_argument("--sessiz", action="store_true")
    a = ap.parse_args(argv)
    if a.kur:
        kur(a.kur)
        return 0
    if a.durum:
        durum()
        return 0
    return yedekle(a.sessiz)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
