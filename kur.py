#!/usr/bin/env python3
"""GurOS kurulumu — bir Obsidian vault'una yapay zekâ hafıza katmanı ekler.

    python kur.py --vault "<vault klasörü>" --ad "<adın>"             # yalnızca planı gösterir, hiçbir şey yazmaz
    python kur.py --vault "<vault klasörü>" --ad "<adın>" --uygula    # kurar
    python kur.py --vault "<vault klasörü>" --kaldir --uygula         # sistemi kaldırır, notlar yerinde kalır

Seçenekler:
    --asistan Logos           asistanın adı
    --ozel "🔒 Özel Alan"     yapay zekâya kapalı klasör (birden çok kez verilebilir)
    --hafiza "🔮 Logos"       asistanın hafıza klasörü
    --proje Projeler          proje notlarının klasörü
    --zamanla [--saat 10:00]  günlük bakımı (indeks + sağlık kontrolü + yedek) zamanla

İki sert kural:
  * Var olan hiçbir not ezilmez. Kurulum iki kez çalıştırılabilir; ikincisi yalnızca eksikleri tamamlar.
  * Hiçbir sır üretilmez, istenmez, yazılmaz.
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEPO = Path(__file__).resolve().parent
SABLON = DEPO / "sablon"
KOD_KAYNAK = DEPO / "guros"
ISARET_BAS, ISARET_SON = "<!-- GUROS:PROTOKOL", "<!-- /GUROS:PROTOKOL -->"
KANCALAR = [("SessionStart", "oturum", None, 30), ("UserPromptSubmit", "istem", None, 15), ("Stop", "dur", None, 15),
            ("PreCompact", "sikistir", None, 10),
            ("PreToolUse", "koruma", "Read|Edit|MultiEdit|Write|Glob|Grep|Bash|PowerShell|NotebookEdit|NotebookRead", 10)]

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass


# ---------------------------------------------------------------- Türkçe ekler (ses uyumu)
def _son_unlu(kelime):
    for h in reversed(kelime.lower().replace("I", "ı").replace("İ", "i")):
        if h in "aıouâû":
            return "kalin_" + ("duz" if h in "aıâ" else "yuvarlak")
        if h in "eiöüî":
            return "ince_" + ("duz" if h in "eiî" else "yuvarlak")
    return "ince_duz"


def _unluyle_biter(kelime):
    return kelime[-1:].lower() in "aıoueiöüâîû"


def ekler(ad):
    son = ad.split()[-1] if ad.split() else ad
    u = _son_unlu(son)
    dort = {"kalin_duz": "ı", "kalin_yuvarlak": "u", "ince_duz": "i", "ince_yuvarlak": "ü"}[u]
    iki = "a" if u.startswith("kalin") else "e"
    sesli = _unluyle_biter(son)
    sert = son[-1:].lower() in "fstkçşhp"
    return {
        "nin": f"{ad}'{'n' if sesli else ''}{dort}n",
        "ye": f"{ad}'{'y' if sesli else ''}{iki}",
        "de": f"{ad}'{'t' if sert else 'd'}{iki}",
        "den": f"{ad}'{'t' if sert else 'd'}{iki}n",
        "yi": f"{ad}'{'y' if sesli else ''}{dort}",
        "sin": f"{ad}'s{dort}n",
    }


# ---------------------------------------------------------------- yardımcılar
class Kurulum:
    def __init__(self, uygula):
        self.uygula, self.plan, self.sorun = uygula, [], []

    def adim(self, aciklama, is_=None):
        self.plan.append(aciklama)
        if self.uygula and is_:
            is_()
            print(f"  [OK]   {aciklama}")
        elif not self.uygula:
            print(f"  [PLAN] {aciklama}")

    def bilgi(self, m):
        print(f"  [ .. ] {m}")

    def hata(self, m):
        self.sorun.append(m)
        print(f"  [EKSİK] {m}")


def oku(yol):
    try:
        with io.open(yol, encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, UnicodeError):
        return ""


def yaz(yol, metin):
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + ".guros-yeni")
    with io.open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write(metin)
    os.replace(gecici, yol)


def py_yolu():
    return Path(sys.executable).as_posix()


def py_kisa():
    return "python" if os.name == "nt" else "python3"


def doldur(metin, d):
    for k, v in d.items():
        metin = metin.replace("{" + k + "}", v)
    return metin


# ---------------------------------------------------------------- kurulum adımları
def kur(a):
    vault = Path(a.vault).expanduser().resolve()
    k = Kurulum(a.uygula)
    print(f"\nGurOS kurulumu — {'UYGULANIYOR' if a.uygula else 'PLAN (hiçbir şey yazılmıyor)'}")
    print(f"Vault: {vault}\n")

    if sys.version_info < (3, 9):
        k.hata(f"Python {sys.version.split()[0]} çok eski; 3.9 veya üstü gerekli.")
        return k
    if vault.exists() and not vault.is_dir():
        k.hata("Verilen yol bir klasör değil.")
        return k
    if not vault.exists():
        k.adim("yeni vault klasörü oluştur", lambda: vault.mkdir(parents=True))
    elif (vault / ".obsidian").is_dir():
        k.bilgi("var olan bir Obsidian vault'u bulundu; notların olduğu gibi kalacak")
    if not shutil.which("git"):
        k.bilgi("git bulunamadı: kurulum için gerekmez, yalnızca isteğe bağlı yedek için gerekir")

    ay_yolu = vault / ".claude" / "guros" / "ayarlar.json"
    mevcut = {}
    if ay_yolu.exists():
        try:
            mevcut = json.loads(oku(ay_yolu))
        except ValueError:
            mevcut = {}
    ay = {
        "ad": mevcut.get("ad") or a.ad or "Kullanıcı",
        "asistan": mevcut.get("asistan") or a.asistan,
        "hafiza_klasoru": mevcut.get("hafiza_klasoru") or a.hafiza,
        "proje_klasoru": mevcut.get("proje_klasoru") or a.proje,
        "ozel_klasorler": mevcut.get("ozel_klasorler") or a.ozel or ["🔒 Özel Alan"],
        "hatirlatma_esigi": mevcut.get("hatirlatma_esigi", 10),
        "recall_sonuc": mevcut.get("recall_sonuc", 3),
        "baglam_siniri": mevcut.get("baglam_siniri", 6000),
    }
    for ad in [ay["hafiza_klasoru"], ay["proje_klasoru"], *ay["ozel_klasorler"]]:
        if re.search(r'[<>:"|?*]', ad) or ad.startswith(("/", "\\")) or ".." in Path(ad).parts:
            k.hata(f"klasör adı kullanılamaz: {ad}")
            return k
    surum = re.search(r'SURUM = "([^"]+)"', oku(KOD_KAYNAK / "ortak.py")).group(1)
    ay["surum"] = surum

    # 1) sistem kodu
    hedef_kod = vault / ".claude" / "guros"
    dosyalar = sorted(p for p in KOD_KAYNAK.iterdir() if p.suffix in (".py", ".json") and p.name != "ayarlar.json")

    def kodu_kopyala():
        hedef_kod.mkdir(parents=True, exist_ok=True)
        for p in dosyalar:
            shutil.copy2(p, hedef_kod / p.name)
    k.adim(f"sistem kodunu {'güncelle' if hedef_kod.exists() else 'kopyala'}: .claude/guros/ ({len(dosyalar)} dosya)", kodu_kopyala)
    k.adim(f"ayarları {'güncelle' if ay_yolu.exists() else 'yaz'}: .claude/guros/ayarlar.json (ad: {ay['ad']}, asistan: {ay['asistan']}, "
           f"özel: {', '.join(ay['ozel_klasorler'])})", lambda: yaz(ay_yolu, json.dumps(ay, ensure_ascii=False, indent=2) + "\n"))

    e_ad, e_as = ekler(ay["ad"]), ekler(ay["asistan"])
    d = {"AD": ay["ad"], "AD_NIN": e_ad["nin"], "AD_YE": e_ad["ye"], "AD_DE": e_ad["de"], "AD_DEN": e_ad["den"], "AD_YI": e_ad["yi"], "ASISTAN": ay["asistan"],
         "ASISTAN_SIN": e_as["sin"], "HAFIZA": ay["hafiza_klasoru"], "PROJE": ay["proje_klasoru"],
         "OZEL_LISTE": ", ".join(f"`{o.rstrip('/')}/`" for o in ay["ozel_klasorler"]),
         "OZEL_KOK": ay["ozel_klasorler"][0].rstrip("/") + "/", "ESIK": str(ay["hatirlatma_esigi"]),
         "PY": py_kisa(), "SURUM": surum}

    # 2) hafıza klasörü ve kök notlar — yalnızca eksik olanlar
    hafiza = vault / ay["hafiza_klasoru"]
    k.adim(f"hafıza klasörü: {ay['hafiza_klasoru']}/Session-Handoffs/", lambda: (hafiza / "Session-Handoffs").mkdir(parents=True, exist_ok=True)) \
        if not (hafiza / "Session-Handoffs").is_dir() else k.bilgi(f"{ay['hafiza_klasoru']}/ zaten var")
    for kaynak in sorted((SABLON / "hafiza").iterdir()):
        hedef = hafiza / kaynak.name
        if not hedef.exists():
            k.adim(f"hafıza dosyası: {ay['hafiza_klasoru']}/{kaynak.name}", lambda h=hedef, s=kaynak: yaz(h, doldur(oku(s), d)))
    for kaynak in sorted((SABLON / "kok").glob("*.md")):
        hedef = vault / kaynak.name
        if not hedef.exists():
            k.adim(f"not: {kaynak.name}", lambda h=hedef, s=kaynak: yaz(h, doldur(oku(s), d)))
    if not (vault / ay["proje_klasoru"]).is_dir():
        k.adim(f"klasör: {ay['proje_klasoru']}/", lambda: (vault / ay["proje_klasoru"]).mkdir(parents=True, exist_ok=True))
    for ozel in ay["ozel_klasorler"]:
        if not (vault / ozel).exists():
            k.adim(f"özel klasör: {ozel}/ (yapay zekâya kapalı)",
                   lambda o=ozel: yaz(vault / o / "Burası özel.md", doldur(oku(SABLON / "kok" / "ozel" / "Burası özel.md"), d)))

    # 3) protokol: CLAUDE.md ve AGENTS.md
    protokol = doldur(oku(SABLON / "PROTOKOL.md"), d).strip() + "\n"
    ajan = protokol.replace(ISARET_SON, doldur(oku(SABLON / "AJAN-EK.md"), d).rstrip() + "\n" + ISARET_SON)
    _protokol_yaz(k, vault / "CLAUDE.md", protokol, import_ile=True)
    _protokol_yaz(k, vault / "AGENTS.md", ajan, import_ile=False)

    # 4) Claude Code komutları
    for kaynak in sorted((SABLON / "komutlar").glob("*.md")):
        hedef = vault / ".claude" / "commands" / kaynak.name
        if not hedef.exists():
            k.adim(f"komut: /{kaynak.stem}", lambda h=hedef, s=kaynak: yaz(h, doldur(oku(s), d)))

    # 5) kancalar ve izin kuralları
    k.adim("kancaları bağla: .claude/settings.json (açılış, mesaj, durma, sıkıştırma, gizlilik koruması)",
           lambda: _ayarlari_birlestir(vault, ay))

    # 6) isteğe bağlı günlük bakım
    if a.zamanla:
        k.adim(f"günlük bakımı zamanla ({a.saat}): indeks + sağlık kontrolü + (kuruluysa) yedek", lambda: _zamanla(vault, a.saat))

    # 7) doğrulama
    if a.uygula:
        print("\nDoğrulama:")
        ortam = dict(os.environ, GUROS_VAULT=str(vault))
        r = subprocess.run([sys.executable, str(hedef_kod / "recall.py"), "kur"], capture_output=True, text=True, encoding="utf-8", env=ortam)
        print("  " + (r.stdout.strip() or r.stderr.strip()))
        r = subprocess.run([sys.executable, str(hedef_kod / "doktor.py")], capture_output=True, text=True, encoding="utf-8", env=ortam)
        print("\n".join("  " + s for s in r.stdout.strip().splitlines()))
        if r.returncode != 0:
            k.sorun.append("doktor hata buldu")
    return k


def _protokol_yaz(k, yol, metin, import_ile):
    mevcut = oku(yol)
    ad = yol.name
    if not yol.exists():
        k.adim(f"{ad}: GurOS protokolünü yaz", lambda: yaz(yol, metin))
    elif ISARET_BAS in mevcut and ISARET_SON in mevcut:
        bas, son = mevcut.index(ISARET_BAS), mevcut.index(ISARET_SON) + len(ISARET_SON)
        yeni = mevcut[:bas] + metin.strip() + mevcut[son:]
        if yeni != mevcut:
            k.adim(f"{ad}: GurOS bloğunu güncelle (blok dışındaki metnine dokunulmaz)", lambda: yaz(yol, yeni))
    elif import_ile and "@CLAUDE.guros.md" in mevcut:
        _protokol_yaz(k, yol.with_name("CLAUDE.guros.md"), metin, import_ile=False)   # set up on an earlier run
    elif import_ile:
        ek = yol.with_name("CLAUDE.guros.md")
        k.adim(f"{ad} zaten var: protokolü CLAUDE.guros.md'ye yaz, {ad} sonuna tek satır '@CLAUDE.guros.md' ekle",
               lambda: (yaz(ek, metin), yaz(yol, mevcut.rstrip("\n") + "\n\n@CLAUDE.guros.md\n")))
    else:
        k.adim(f"{ad} zaten var: GurOS bloğunu dosyanın sonuna ekle (var olan metne dokunulmaz)",
               lambda: yaz(yol, mevcut.rstrip("\n") + "\n\n" + metin))


def _kanca_komutu(vault, alt):
    return f'"{py_yolu()}" "{(vault / ".claude" / "guros" / "kancalar.py").as_posix()}" {alt}'


def _ayarlari_birlestir(vault, ay):
    yol = vault / ".claude" / "settings.json"
    try:
        veri = json.loads(oku(yol)) if yol.exists() else {}
    except ValueError:
        raise SystemExit(".claude/settings.json geçerli JSON değil; elle düzelt ve yeniden dene (dosyaya dokunulmadı).")
    if yol.exists():
        shutil.copy2(yol, yol.with_name(f"settings.json.yedek-{dt.datetime.now():%Y%m%d-%H%M%S}"))
    kancalar = veri.setdefault("hooks", {})
    for olay, alt, eslesme, sure in KANCALAR:
        gruplar = [g for g in kancalar.get(olay, [])
                   if not any("/.claude/guros/kancalar.py" in h.get("command", "") for h in g.get("hooks", []))]
        grup = {"hooks": [{"type": "command", "command": _kanca_komutu(vault, alt), "timeout": sure}]}
        if eslesme:
            grup = {"matcher": eslesme, **grup}
        gruplar.append(grup)
        kancalar[olay] = gruplar
    izin = veri.setdefault("permissions", {}).setdefault("deny", [])
    for ozel in ay["ozel_klasorler"]:
        yer = f"(./{ozel.rstrip('/')}/**)"
        # Claude Code consults only Read and Edit path rules (Read also covers Grep/Glob, Edit covers Write);
        # Write/Glob/Grep path rules are ignored with a startup warning, so earlier versions' copies are dropped
        izin[:] = [r for r in izin if r not in (f"Write{yer}", f"Glob{yer}", f"Grep{yer}")]
        for arac in ("Read", "Edit"):
            if arac + yer not in izin:
                izin.append(arac + yer)
    yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")


def _gorev_adi(vault):
    return "GurOS Bakim - " + re.sub(r"[^A-Za-z0-9 _-]+", "", vault.name)[:40]


def _zamanla(vault, saat):
    betik = (vault / ".claude" / "guros" / "bakim.py")
    if os.name == "nt":
        pyw = Path(sys.executable).with_name("pythonw.exe")
        calistir = pyw if pyw.exists() else Path(sys.executable)
        subprocess.run(["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", saat, "/TN", _gorev_adi(vault),
                        "/TR", f'"{calistir}" "{betik}"'], check=True, capture_output=True)
    else:
        satir = f'{int(saat.split(":")[1])} {int(saat.split(":")[0])} * * * "{sys.executable}" "{betik}" >/dev/null 2>&1  # GurOS'
        eski = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        if str(betik) not in eski:
            subprocess.run(["crontab", "-"], input=eski.rstrip("\n") + ("\n" if eski.strip() else "") + satir + "\n", text=True, check=True)


def kaldir(a):
    vault = Path(a.vault).expanduser().resolve()
    k = Kurulum(a.uygula)
    print(f"\nGurOS kaldırma — {'UYGULANIYOR' if a.uygula else 'PLAN'}\nVault: {vault}\n")
    yol = vault / ".claude" / "settings.json"
    if yol.exists():
        def temizle():
            veri = json.loads(oku(yol))
            for olay in list(veri.get("hooks", {})):
                veri["hooks"][olay] = [g for g in veri["hooks"][olay]
                                       if not any("/.claude/guros/kancalar.py" in h.get("command", "") for h in g.get("hooks", []))]
                if not veri["hooks"][olay]:
                    del veri["hooks"][olay]
            yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
        k.adim("kancaları .claude/settings.json'dan çıkar (gizlilik izin kuralları koruma için kalır)", temizle)
    if (vault / ".claude" / "guros").exists():
        k.adim("sistem kodunu sil: .claude/guros/", lambda: shutil.rmtree(vault / ".claude" / "guros"))
    if os.name == "nt":
        k.adim("varsa günlük bakım görevini sil", lambda: subprocess.run(["schtasks", "/Delete", "/F", "/TN", _gorev_adi(vault)], capture_output=True))
    k.bilgi("notların, hafıza klasörün, CLAUDE.md ve AGENTS.md yerinde kalır; istersen GurOS bloğunu elle silebilirsin")
    return k


def main(argv):
    ap = argparse.ArgumentParser(description="GurOS kurulumu", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--vault")
    ap.add_argument("--ad")
    ap.add_argument("--asistan", default="Logos")
    ap.add_argument("--hafiza", default="🔮 Logos")
    ap.add_argument("--proje", default="Projeler")
    ap.add_argument("--ozel", action="append")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--kaldir", action="store_true")
    ap.add_argument("--zamanla", action="store_true")
    ap.add_argument("--saat", default="10:00")
    a = ap.parse_args(argv)
    if not a.vault:
        if sys.stdin.isatty():
            a.vault = input("Vault klasörü (yoksa oluşturulur): ").strip().strip('"')
            if not a.kaldir and not a.ad:
                a.ad = input("Adın: ").strip() or None
        else:
            ap.error("--vault gerekli")
    if not re.fullmatch(r"\d{1,2}:\d{2}", a.saat):
        ap.error("--saat SS:DD biçiminde olmalı")
    k = kaldir(a) if a.kaldir else kur(a)
    if k.sorun:
        print("\nSorunlar:\n" + "\n".join(f"  - {s}" for s in k.sorun))
        return 1
    if not a.uygula:
        print("\nPlan bu. Uygulamak için aynı komutu --uygula ile çalıştır.")
    elif not a.kaldir:
        print(f"\nKurulum tamam. Şimdi:\n  1. Obsidian'da bu klasörü vault olarak aç: {Path(a.vault).expanduser().resolve()}"
              "\n  2. Bu klasörde Claude Code'u başlat (terminalde: cd <vault> ; claude) ve merhaba de."
              "\n  3. İstersen yedek: python .claude/guros/yedek.py --kur <ÖZEL github repo adresi>")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
