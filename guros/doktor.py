"""Health check: is every part of GurOS wired and working? Measures, never changes anything.

    python doktor.py            # full report
    python doktor.py --sessiz   # only problems (for the daily maintenance run)

Exit code 1 when something is broken (✗); warnings (⚠) do not fail.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

OLAYLAR = {"SessionStart": "oturum", "UserPromptSubmit": "istem", "Stop": "dur", "PreCompact": "sikistir", "PreToolUse": "koruma"}


class Rapor:
    def __init__(self, sessiz):
        self.sessiz, self.hata, self.uyari = sessiz, 0, 0

    def iyi(self, m):
        if not self.sessiz:
            print(f"  ✓ {m}")

    def uyar(self, m):
        self.uyari += 1
        print(f"  ⚠ {m}")

    def kotu(self, m):
        self.hata += 1
        print(f"  ✗ {m}")


CLAUDE_EN_AZ = (2, 1, 139)       # hooks are written in exec form ("args"), which arrived in this release


def _kanca_metni(h):
    return " ".join([str(h.get("command", "")), *(str(x) for x in (h.get("args") or []))]).replace("\\", "/").replace('"', "")


def _claude_surumu():
    """Installed Claude Code version as a tuple, or None when it is not installed or does not answer."""
    yol = None if os.environ.get("GUROS_CLAUDE") == "0" else shutil.which("claude")
    if not yol:
        return None
    try:
        cikti = subprocess.run([yol, "--version"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", cikti or "")
    return tuple(int(x) for x in m.groups()) if m else None


def _kanca_calistir(vault, olay, girdi):
    ortam = dict(os.environ, GUROS_VAULT=str(vault))
    return subprocess.run([sys.executable, str(ortak.KOD / "kancalar.py"), olay], input=json.dumps(girdi),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", env=ortam, timeout=60)


def kontrol(sessiz=False):
    r = Rapor(sessiz)
    vault = ortak.vault_kok()
    ay = ortak.ayarlar(vault)
    hafiza = ortak.hafiza_dizini(vault, ay)
    if not sessiz:
        print(f"GurOS doktor — {vault}")

    if sys.version_info >= (3, 9):
        r.iyi(f"Python {sys.version.split()[0]}")
    else:
        r.kotu(f"Python {sys.version.split()[0]} çok eski; 3.9 veya üstü gerekli")
    if "WindowsApps" in sys.executable:
        r.uyar("Microsoft Store Python'u kullanılıyor; bazı klasörleri farklı görebilir. python.org sürümü önerilir.")

    for ad, zorunlu in (("Core.md", None), ("Facts.md", None), ("Threads.md", "## Aktif"),
                        ("Last-Session.md", None), ("📌 Kararlar.md", None), ("Journal.md", None)):
        yol = hafiza / ad
        if not yol.exists():
            r.kotu(f"hafıza dosyası eksik: {ay['hafiza_klasoru']}/{ad}")
        elif zorunlu and zorunlu not in ortak.oku(yol):
            r.kotu(f"{ad} içinde '{zorunlu}' başlığı yok (kancalar bu başlığı okuyor)")
    if (hafiza / "Session-Handoffs").is_dir():
        r.iyi(f"hafıza klasörü tamam: {ay['hafiza_klasoru']}/")
    else:
        r.kotu(f"{ay['hafiza_klasoru']}/Session-Handoffs/ klasörü yok")

    claude = vault / "CLAUDE.md"
    metin = ortak.oku(claude)
    if "GUROS" not in metin and "@CLAUDE.guros.md" not in metin:
        r.kotu("CLAUDE.md GurOS protokolünü içermiyor (kur.py yeniden çalıştırılabilir)")
    elif len(metin.encode("utf-8")) > 20000:
        r.uyar(f"CLAUDE.md {len(metin.encode('utf-8')) // 1024} KB; her sohbete yükleniyor, 20 KB altında tut")
    else:
        r.iyi("CLAUDE.md protokolü yerinde")
    if not (vault / "AGENTS.md").exists():
        r.uyar("AGENTS.md yok; Codex gibi diğer ajanlar protokolü göremez")

    try:
        with io.open(vault / ".claude" / "settings.json", encoding="utf-8") as f:
            kancalar = json.load(f).get("hooks", {})
    except (OSError, ValueError):
        kancalar = None
    if kancalar is None:
        r.kotu(".claude/settings.json okunamadı; kancalar bağlı değil")
    else:
        bizim = {olay: [h for grup in kancalar.get(olay, []) for h in grup.get("hooks", []) if "kancalar.py" in _kanca_metni(h)]
                 for olay in OLAYLAR}
        eksik = [olay for olay, alt in OLAYLAR.items() if not any(_kanca_metni(h).endswith(" " + alt) for h in bizim[olay])]
        if eksik:
            r.kotu("bağlı olmayan kancalar: " + ", ".join(eksik) + " (kur.py yeniden çalıştırılabilir)")
        else:
            r.iyi("5 kanca bağlı (açılış, mesaj, durma, sıkıştırma, gizlilik)")
        eski_bicim = False
        for h in {id(h): h for liste in bizim.values() for h in liste}.values():
            if h.get("args"):
                yorumlayici, betik = h.get("command", ""), str(h["args"][0])
            else:                                   # shell form written by 1.0.0: "<python>" "<script>" <event>
                parca = h.get("command", "").split('"')
                yorumlayici, betik = (parca[1], parca[3]) if len(parca) > 3 else ("", "")
                eski_bicim = True
            if yorumlayici and Path(yorumlayici).is_absolute() and not Path(yorumlayici).exists():
                r.kotu(f"kancaların Python yolu yok: {yorumlayici} (Python taşındıysa kur.py'yi yeniden çalıştır)")
                break
            if betik and not Path(betik).exists():
                r.kotu(f"kanca betiği yok: {betik} (vault taşındıysa kur.py'yi yeniden çalıştır)")
                break
        if eski_bicim:
            r.uyar("kancalar eski biçimde (Git Bash olmayan Windows'ta çalışmaz); kur.py --uygula ile güncelle")
        surum = _claude_surumu()
        if surum and surum < CLAUDE_EN_AZ:
            r.uyar(f"Claude Code {'.'.join(map(str, surum))} eski; kancalar {'.'.join(map(str, CLAUDE_EN_AZ))}+ ister. "
                   "Güncelle: claude update")

    if ay.get("ozel_klasorler"):
        ornek = ay["ozel_klasorler"][0]
        dene = lambda arac, girdi: _kanca_calistir(vault, "koruma", {"cwd": str(vault), "tool_name": arac, "tool_input": girdi}).returncode
        sonuc = {"adıyla okuma": (dene("Bash", {"command": f'cat "{ornek}/gunluk.md"'}), 2),
                 "kökten özyinelemeli arama": (dene("Bash", {"command": "grep -r kelime ."}), 2),
                 "kökten Grep": (dene("Grep", {"pattern": "kelime"}), 2),
                 "sıradan komut": (dene("Bash", {"command": "ls"}), 0)}
        yanlis = [f"{ad}={gelen} (beklenen {beklenen})" for ad, (gelen, beklenen) in sonuc.items() if gelen != beklenen]
        if yanlis:
            r.kotu("gizlilik koruması beklenen gibi davranmadı: " + ", ".join(yanlis))
        else:
            r.iyi(f"gizlilik koruması çalışıyor: {', '.join(ay['ozel_klasorler'])}")
        try:
            with io.open(vault / ".claude" / "settings.json", encoding="utf-8") as f:
                ret = json.load(f).get("permissions", {}).get("deny", [])
        except (OSError, ValueError):
            ret = []
        eksik = [o for o in ay["ozel_klasorler"] if f"Read(./{o.rstrip('/')}/**)" not in ret]
        if eksik:
            r.uyar("izin kuralı eksik (ikinci kat koruma): Read(./" + "/**), Read(./".join(eksik) + "/**) — kur.py yeniden çalıştırılabilir")
    else:
        r.uyar("özel klasör tanımlı değil; ayarlar.json → ozel_klasorler")

    try:
        import recall
        t0 = time.time()
        ix = recall.indeks(vault)
        sizan = [p for p in ix["dosyalar"] if ortak.ozel_mi(p, ay)]
        if sizan:
            r.kotu(f"Recall özel alandan {len(sizan)} dosya indekslemiş!")
        else:
            r.iyi(f"Recall: {len(ix['dosyalar'])} not, {ix['n']} parça ({time.time() - t0:.1f} sn)")
    except Exception as e:
        r.kotu(f"Recall indeksi kurulamadı: {e}")

    if (vault / ".git").exists():
        try:
            son = subprocess.run(["git", "-C", str(vault), "log", "-1", "--format=%ct"], capture_output=True, text=True, timeout=30).stdout.strip()
            gun = (time.time() - int(son)) / 86400 if son else None
            if gun is None:
                r.uyar("yedek kurulu ama hiç commit yok (yedek.py)")
            elif gun > 2:
                r.uyar(f"son yedek {gun:.0f} gün önce")
            else:
                r.iyi("yedek güncel")
        except (OSError, ValueError, subprocess.SubprocessError):
            r.uyar("yedek durumu okunamadı")

    if not sessiz or r.hata or r.uyari:
        print(f"\nSonuç: {r.hata} hata, {r.uyari} uyarı.")
    return 1 if r.hata else 0


if __name__ == "__main__":
    sys.exit(kontrol("--sessiz" in sys.argv[1:]))
