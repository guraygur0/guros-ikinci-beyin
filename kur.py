#!/usr/bin/env python3
"""GurOS kurulumu — bir Obsidian vault'una yapay zekâ hafıza katmanı ekler.

    python kur.py                                                  # sihirbaz: sorar, planı gösterir, onaylarsan kurar
    python kur.py --vault "<vault klasörü>" --ad "<adın>"            # yalnızca planı gösterir, hiçbir şey yazmaz
    python kur.py --vault "<vault klasörü>" --ad "<adın>" --uygula   # kurar
    python kur.py --vault "<vault klasörü>" --kaldir --uygula        # kaldırır, notların yerinde kalır
    python kur.py --vaultlar                                       # bu bilgisayardaki Obsidian vault'larını listeler

Seçenekler (verilmeyenler önceki kurulumdan, o da yoksa varsayılandan alınır):
    --asistan Logos           asistanın adı
    --ozel "Günlük"           yapay zekâya kapalı klasör; birden çok kez verilebilir (varsayılan: "🔒 Özel Alan")
    --hafiza "🔮 Logos"       asistanın hafıza klasörü
    --proje Projeler          proje notlarının klasörü
    --zamanla [--saat 10:00]  günlük bakımı (indeks + sağlık kontrolü + varsa yedek) zamanla

İki sert kural:
  * Var olan hiçbir not ezilmez. Kurulum tekrar çalıştırılabilir; yalnızca eksikleri tamamlar ve sistemi günceller.
  * Hiçbir sır üretilmez, istenmez, yazılmaz.
"""
import argparse
import datetime as dt
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

DEPO = Path(__file__).resolve().parent
SABLON = DEPO / "sablon"
KOD_KAYNAK = DEPO / "guros"
sys.path.insert(0, str(KOD_KAYNAK))
import ortak  # noqa: E402  (Turkish folding and the version number live in one place)

SURUM = ortak.SURUM
ISARET_BAS, ISARET_SON = "<!-- GUROS:PROTOKOL", "<!-- /GUROS:PROTOKOL -->"
VARSAYILAN_OZEL = "🔒 Özel Alan"
KANCALAR = [("SessionStart", "oturum", None, 30), ("UserPromptSubmit", "istem", None, 15), ("Stop", "dur", None, 15),
            ("PreCompact", "sikistir", None, 10),
            ("PreToolUse", "koruma", "Read|Edit|MultiEdit|Write|Glob|Grep|Bash|PowerShell|NotebookEdit|NotebookRead", 10)]
IZINLI_BETIKLER = ["baglam", "recall", "devir", "epizot", "proje", "doktor"]   # run without a prompt; yedek.py pushes, so it asks
HAFIZA_DOSYALARI = ["Core.md", "Facts.md", "Threads.md", "Last-Session.md", "📌 Kararlar.md", "Journal.md"]
GRUPLAR = ["Notlar", "Hafıza", "Asistan kuralları", "Claude Code", "Sistem", "Bakım"]
GRUP_SIMGE = {"Notlar": "📝", "Hafıza": "🔮", "Asistan kuralları": "📜", "Claude Code": "🤖", "Sistem": "⚙️ ", "Bakım": "🕙"}
CLAUDE_EN_AZ = "2.1.139"          # hooks use exec form ("args"), added in that release
_OZEL_KOKLER = ("gunlu", "journal", "diary", "diari", "ozel", "private", "privat", "kisisel", "personal", "gizli",
                "secret", "mahrem")
_OZEL_DEGIL = ("ozellik",)        # "Özellikler" (features) is not private


class Iptal(Exception):
    """The user stopped the wizard (Ctrl+C or end of input)."""


# ---------------------------------------------------------------- görünüm
def _windows_vt():
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mod = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(mod)):
            return False
        return bool(mod.value & 0x0004) or bool(k.SetConsoleMode(h, mod.value | 0x0004))
    except Exception:
        return False


class Renk:
    """ANSI colours only on a real terminal; NO_COLOR, pipes and agents get plain text."""

    def __init__(self, akis):
        try:
            self.acik = bool(akis.isatty()) and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"
        except (AttributeError, ValueError):
            self.acik = False
        if self.acik and os.name == "nt":
            self.acik = _windows_vt()

    def _b(self, kod, m):
        return f"\033[{kod}m{m}\033[0m" if self.acik else m

    def kalin(self, m):
        return self._b("1", m)

    def soluk(self, m):
        return self._b("2", m)

    def yesil(self, m):
        return self._b("32", m)

    def sari(self, m):
        return self._b("33", m)

    def kirmizi(self, m):
        return self._b("31", m)

    def mavi(self, m):
        return self._b("36", m)

    def mor(self, m):
        return self._b("35", m)


R = Renk(sys.stdout)
ISARETLER = {"+": R.yesil("+"), "~": R.sari("~"), "-": R.kirmizi("−"), "=": R.soluk("·")}


def _baslik():
    satir = f"  GurOS {SURUM} · Obsidian için yapay zekâ ikinci beyin  "
    print()
    print("  " + R.mor("╭" + "─" * len(satir) + "╮"))
    print("  " + R.mor("│") + R.kalin(satir) + R.mor("│"))
    print("  " + R.mor("╰" + "─" * len(satir) + "╯"))


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


# ---------------------------------------------------------------- dosya ve Python yardımcıları
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


def doldur(metin, d):
    for k, v in d.items():
        metin = metin.replace("{" + k + "}", v)
    return metin


def _python_calisir(komut):
    """True if `komut` starts a Python 3.9+ (the Windows Store stub prints an ad and fails)."""
    try:
        r = subprocess.run([*komut, "-c", "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"],
                           capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def py_kisa():
    """How the assistant should call Python in commands it runs inside the vault."""
    adaylar = ["python", "py"] if os.name == "nt" else ["python3", "python"]
    for ad in adaylar:
        yol = shutil.which(ad)
        if yol and _python_calisir([yol] + (["-3"] if ad == "py" else [])):
            return ad
    return f'"{Path(sys.executable).as_posix()}"'


def hook_python():
    """Interpreter for the hooks. On macOS/Linux the PATH entry survives Python upgrades better than the versioned path."""
    if os.name != "nt":
        yol = shutil.which("python3")
        if yol and _python_calisir([yol]):
            return yol
    return str(Path(sys.executable))


# ---------------------------------------------------------------- keşif
def _obsidian_json_yollari():
    ozel = os.environ.get("GUROS_OBSIDIAN_JSON")
    if ozel:
        return [Path(ozel)]
    ev = Path.home()
    if os.name == "nt":
        tabanlar = [Path(os.environ.get("APPDATA") or ev / "AppData" / "Roaming") / "obsidian"]
    elif sys.platform == "darwin":
        tabanlar = [ev / "Library" / "Application Support" / "obsidian"]
    else:
        tabanlar = [Path(os.environ.get("XDG_CONFIG_HOME") or ev / ".config") / "obsidian",
                    ev / ".var" / "app" / "md.obsidian.Obsidian" / "config" / "obsidian",
                    ev / "snap" / "obsidian" / "current" / ".config" / "obsidian"]
    return [t / "obsidian.json" for t in tabanlar]


def obsidian_vaultlari():
    """Vaults Obsidian knows about on this machine, most recently opened first: [(name, path)]."""
    bulunan = {}
    for j in _obsidian_json_yollari():
        try:
            veri = json.loads(oku(j) or "{}")
        except ValueError:
            continue
        for v in (veri.get("vaults") or {}).values():
            if not isinstance(v, dict) or not v.get("path"):
                continue
            yol = Path(v["path"])
            if yol.is_dir():
                bulunan[str(yol.resolve())] = (v.get("ts") or 0, yol.resolve())
    return [(y.name, y) for _, y in sorted(bulunan.values(), key=lambda t: -t[0])]


def _ozel_gibi(ad):
    kelimeler = ortak.sade(ad).split()
    return any(w.startswith(k) and not w.startswith(_OZEL_DEGIL) for w in kelimeler for k in _OZEL_KOKLER)


def ozel_adaylar(vault, haric=()):
    """Folders (two levels deep) whose NAME suggests they are private. Contents are never opened."""
    out = []
    if not Path(vault).is_dir():
        return out
    haric = {ortak.katla(h) for h in haric}
    try:
        ust = sorted(p for p in Path(vault).iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError:
        return out
    for d in ust:
        if ortak.katla(d.name) in haric:
            continue
        if _ozel_gibi(d.name):
            out.append(d.name)
            continue
        try:
            for e in sorted(d.iterdir()):
                if e.is_dir() and not e.name.startswith(".") and _ozel_gibi(e.name):
                    out.append(f"{d.name}/{e.name}")
        except OSError:
            pass
    return out


def kurulu_ayarlar(vault):
    yol = Path(vault) / ".claude" / "guros" / "ayarlar.json"
    if not yol.exists():
        return None
    try:
        return json.loads(oku(yol))
    except ValueError:
        return {}


def claude_yolu():
    if os.environ.get("GUROS_CLAUDE") == "0":
        return None
    return shutil.which("claude")


def _icinde(alt, ust):
    alt, ust = Path(alt).resolve(), Path(ust).resolve()
    return alt == ust or ust in alt.parents


# ---------------------------------------------------------------- plan
class Plan:
    """Every change is a step. Nothing is written until uygula(); goster() prints the same steps as a plan."""

    def __init__(self, baslik, vault):
        self.baslik, self.vault = baslik, vault
        self.adimlar, self.bilgiler, self.uyarilar, self.sorunlar = [], [], [], []

    def adim(self, grup, metin, is_=None, isaret="+"):
        self.adimlar.append((grup, isaret, metin, is_))

    def bilgi(self, m):
        self.bilgiler.append(m)

    def uyari(self, m):
        self.uyarilar.append(m)

    def hata(self, m):
        self.sorunlar.append(m)

    def _sirali(self):
        sira = {g: i for i, g in enumerate(GRUPLAR)}
        return sorted(self.adimlar, key=lambda a: sira.get(a[0], len(GRUPLAR)))

    def _ust(self, durum):
        print(f"\n  {R.kalin(self.baslik)} {R.soluk('— ' + durum)}")
        print(f"  {R.soluk('Vault:')} {self.vault}")
        for b in self.bilgiler:
            print(f"  {R.soluk('· ' + b)}")

    def goster(self):
        self._ust("plan, henüz hiçbir şey yazılmadı")
        grup = None
        for g, isaret, metin, _ in self._sirali():
            if g != grup:
                grup = g
                print(f"\n  {GRUP_SIMGE.get(g, '•')} {R.kalin(g)}")
            print(f"     {ISARETLER.get(isaret, isaret)} {metin}")
        if not self.adimlar and not self.sorunlar:
            print(f"\n  {R.yesil('Her şey güncel; yapılacak bir şey yok.')}")
        for u in self.uyarilar:
            print(f"\n  {R.sari('!')} {u}")
        for s in self.sorunlar:
            print(f"\n  {R.kirmizi('✗')} {s}")

    def uygula(self):
        self._ust("uygulanıyor")
        grup = None
        for g, _, metin, is_ in self._sirali():
            if g != grup:
                grup = g
                print(f"\n  {GRUP_SIMGE.get(g, '•')} {R.kalin(g)}")
            try:
                if is_:
                    is_()
            except Exception as e:                      # stop at the first failure; later steps may depend on it
                print(f"     {R.kirmizi('✗')} {metin}\n       {R.kirmizi(str(e))}")
                self.sorunlar.append(f"{metin}: {e}")
                return False
            print(f"     {R.yesil('✓')} {metin}")
        return True


# ---------------------------------------------------------------- kurulum planı
def kur_plani(vault, s):
    """Build the install (or update) plan. `s` holds what the user chose; missing keys fall back to the previous install."""
    vault = Path(vault).expanduser().resolve()
    p = Plan("GurOS kurulumu", vault)
    if sys.version_info < (3, 9):
        p.hata(f"Python {sys.version.split()[0]} çok eski; 3.9 veya üstü gerekli.")
        return p, None
    if vault.exists() and not vault.is_dir():
        p.hata("Verilen yol bir klasör değil.")
        return p, None
    if _icinde(vault, DEPO):
        p.hata(f"Bu, kurulum paketinin kendi klasörü ({DEPO}). Vault başka bir yerde olmalı.")
        return p, None
    if _icinde(DEPO, vault):
        p.hata(f"Kurulum paketi vault'un içinde duruyor ({DEPO}). Paketi vault dışına taşı (ör. ev klasörüne) "
               "ve yeniden çalıştır; yoksa paketin belgeleri notların arasına karışır.")
        return p, None

    mevcut = kurulu_ayarlar(vault) or {}
    if not vault.exists():
        p.adim("Notlar", f"yeni vault klasörü: {vault.name}/", lambda: vault.mkdir(parents=True))
    elif mevcut:
        p.bilgi(f"GurOS {mevcut.get('surum', '?')} zaten kurulu: güncellenecek, notların ve hafıza aynen kalır")
    elif (vault / ".obsidian").is_dir():
        p.bilgi("var olan bir Obsidian vault'u: notların olduğu gibi kalır")
    if not shutil.which("git"):
        p.bilgi("git yok: kurulum için gerekmez, yalnızca isteğe bağlı yedek için gerekir")

    ay = {
        "ad": s.get("ad") or mevcut.get("ad") or "Kullanıcı",
        "asistan": s.get("asistan") or mevcut.get("asistan") or "Logos",
        "hafiza_klasoru": s.get("hafiza") or mevcut.get("hafiza_klasoru") or "🔮 Logos",
        "proje_klasoru": s.get("proje") or mevcut.get("proje_klasoru") or "Projeler",
        "ozel_klasorler": list(dict.fromkeys(s.get("ozel") or mevcut.get("ozel_klasorler") or [VARSAYILAN_OZEL])),
        "hatirlatma_esigi": mevcut.get("hatirlatma_esigi", 10),
        "recall_sonuc": mevcut.get("recall_sonuc", 3),
        "baglam_siniri": mevcut.get("baglam_siniri", 6000),
        "surum": SURUM,
    }
    ay["ozel_klasorler"] = [o.strip().strip("/\\") for o in ay["ozel_klasorler"] if o.strip().strip("/\\")]
    for ad in [ay["hafiza_klasoru"], ay["proje_klasoru"], *ay["ozel_klasorler"]]:
        if re.search(r'[<>:"|?*]', ad) or ad.startswith(("/", "\\")) or ".." in Path(ad).parts:
            p.hata(f"klasör adı kullanılamaz: {ad}  (vault içinde göreli bir ad olmalı; < > : \" | ? * olmadan)")
            return p, None
    if not ay["ozel_klasorler"]:
        p.hata("en az bir özel klasör gerekli")
        return p, None

    acik = [a for a in ozel_adaylar(vault, haric={ay["hafiza_klasoru"]}) if not ortak.ozel_mi(a, ay)]
    if acik:
        bayraklar = " ".join(f'--ozel "{o}"' for o in ay["ozel_klasorler"] + acik)
        p.uyari("Adından özel olduğu anlaşılan klasörler yapay zekâya AÇIK kalacak (içlerine bakılmadı): "
                + ", ".join(f'"{a}"' for a in acik) + "\n    Kapatmak için kurulumu şu bayraklarla çalıştır: " + bayraklar)

    py = py_kisa()
    e_ad, e_as = ekler(ay["ad"]), ekler(ay["asistan"])
    d = {"AD": ay["ad"], "AD_NIN": e_ad["nin"], "AD_YE": e_ad["ye"], "AD_DE": e_ad["de"], "AD_DEN": e_ad["den"],
         "AD_YI": e_ad["yi"], "ASISTAN": ay["asistan"], "ASISTAN_SIN": e_as["sin"], "ASISTAN_NIN": e_as["nin"],
         "ASISTAN_YE": e_as["ye"], "HAFIZA": ay["hafiza_klasoru"], "PROJE": ay["proje_klasoru"],
         "OZEL_LISTE": ", ".join(f"`{o}/`" for o in ay["ozel_klasorler"]),
         "OZEL_KOK": ay["ozel_klasorler"][0] + "/", "ESIK": str(ay["hatirlatma_esigi"]), "PY": py, "SURUM": SURUM}

    # Notlar — only what is missing
    aciklama = {"🎯 Hedefler.md": "açık hedeflerin; her sohbetin başında görünür", "⚡ Quick Notes.md": "hızlı yakalama",
                "👋 Başlarken.md": "nasıl kullanılır (okuyunca silebilirsin)"}
    for kaynak in sorted((SABLON / "kok").glob("*.md"), key=lambda k: list(aciklama).index(k.name) if k.name in aciklama else 9):
        hedef = vault / kaynak.name
        if not hedef.exists():
            p.adim("Notlar", f"{kaynak.name} — {aciklama.get(kaynak.name, 'not')}", lambda h=hedef, k=kaynak: yaz(h, doldur(oku(k), d)))
    if not (vault / ay["proje_klasoru"]).is_dir():
        p.adim("Notlar", f"{ay['proje_klasoru']}/ — her proje için bir not",
               lambda: (vault / ay["proje_klasoru"]).mkdir(parents=True, exist_ok=True))
    for ozel in ay["ozel_klasorler"]:
        if not (vault / ozel).exists():
            p.adim("Notlar", f"{ozel}/ — yapay zekâya kapalı özel alan",
                   lambda o=ozel: yaz(vault / o / "Burası özel.md", doldur(oku(SABLON / "kok" / "ozel" / "Burası özel.md"), d)))
        else:
            p.adim("Notlar", f"{ozel}/ — var olan klasör; yapay zekâya kapalı (içine dokunulmaz)", isaret="=")

    # Hafıza
    hafiza = vault / ay["hafiza_klasoru"]
    eksik = [ad for ad in HAFIZA_DOSYALARI if not (hafiza / ad).exists()]
    if eksik or not (hafiza / "Session-Handoffs").is_dir():
        def hafizayi_kur():
            (hafiza / "Session-Handoffs").mkdir(parents=True, exist_ok=True)
            for ad in eksik:
                yaz(hafiza / ad, doldur(oku(SABLON / "hafiza" / ad), d))
        adlar = ", ".join(Path(a).stem for a in eksik) + (" ve " if eksik else "") + "Session-Handoffs/"
        p.adim("Hafıza", f"{ay['hafiza_klasoru']}/ — {adlar}", hafizayi_kur)

    # Asistan kuralları
    protokol = doldur(oku(SABLON / "PROTOKOL.md"), d).strip() + "\n"
    ajan = protokol.replace(ISARET_SON, doldur(oku(SABLON / "AJAN-EK.md"), d).rstrip() + "\n" + ISARET_SON)
    _protokol_adimi(p, vault / "CLAUDE.md", protokol, "Claude Code için kurallar ve hafıza protokolü", import_ile=True)
    _protokol_adimi(p, vault / "AGENTS.md", ajan, "aynı kurallar Codex ve diğer ajanlar için", import_ile=False)

    # Claude Code
    komutlar = [k for k in sorted((SABLON / "komutlar").glob("*.md")) if not (vault / ".claude" / "commands" / k.name).exists()]
    if komutlar:
        p.adim("Claude Code", f"{len(komutlar)} komut: " + " ".join("/" + k.stem for k in komutlar),
               lambda: [yaz(vault / ".claude" / "commands" / k.name, doldur(oku(k), d)) for k in komutlar])
    ayar_yolu = vault / ".claude" / "settings.json"
    p.adim("Claude Code", ".claude/settings.json — 5 kanca, gizlilik kuralları, izinler"
           + (" (önce yedeklenir, başka ayarların korunur)" if ayar_yolu.exists() else ""),
           lambda: _ayarlari_birlestir(vault, ay, mevcut, py), isaret="~" if ayar_yolu.exists() else "+")

    # Sistem
    hedef_kod = vault / ".claude" / "guros"
    dosyalar = sorted(k for k in KOD_KAYNAK.iterdir() if k.suffix in (".py", ".json") and k.name != "ayarlar.json")

    def kodu_kopyala():
        hedef_kod.mkdir(parents=True, exist_ok=True)
        for k in dosyalar:
            shutil.copy2(k, hedef_kod / k.name)
    p.adim("Sistem", f".claude/guros/ — sistem kodu ({len(dosyalar)} dosya, yalnız Python standart kütüphanesi)",
           kodu_kopyala, isaret="~" if hedef_kod.exists() else "+")
    p.adim("Sistem", f".claude/guros/ayarlar.json — ad: {ay['ad']} · asistan: {ay['asistan']} · özel: "
           + ", ".join(ay["ozel_klasorler"]),
           lambda: yaz(hedef_kod / "ayarlar.json", json.dumps(ay, ensure_ascii=False, indent=2) + "\n"),
           isaret="~" if mevcut else "+")

    if s.get("zamanla"):
        p.adim("Bakım", f"her gün {s.get('saat') or '10:00'}: arama indeksi, sağlık kontrolü, varsa yedek",
               lambda: _zamanla(vault, s.get("saat") or "10:00"))
    return p, ay


def _protokol_adimi(p, yol, metin, aciklama, import_ile):
    mevcut = oku(yol)
    ad = yol.name
    if not yol.exists():
        p.adim("Asistan kuralları", f"{ad} — {aciklama}", lambda: yaz(yol, metin))
    elif ISARET_BAS in mevcut and ISARET_SON in mevcut:
        bas, son = mevcut.index(ISARET_BAS), mevcut.index(ISARET_SON) + len(ISARET_SON)
        yeni = mevcut[:bas] + metin.strip() + mevcut[son:]
        if yeni != mevcut:
            p.adim("Asistan kuralları", f"{ad} — GurOS bloğu güncellenir (blok dışındaki metnine dokunulmaz)",
                   lambda: yaz(yol, yeni), isaret="~")
    elif import_ile and "@CLAUDE.guros.md" in mevcut:
        _protokol_adimi(p, yol.with_name("CLAUDE.guros.md"), metin, aciklama, import_ile=False)
    elif import_ile:
        ek = yol.with_name("CLAUDE.guros.md")
        p.adim("Asistan kuralları", f"{ad} zaten var: kurallar CLAUDE.guros.md'ye yazılır, {ad} sonuna tek satır "
               "'@CLAUDE.guros.md' eklenir", lambda: (yaz(ek, metin), yaz(yol, mevcut.rstrip("\n") + "\n\n@CLAUDE.guros.md\n")),
               isaret="~")
    else:
        p.adim("Asistan kuralları", f"{ad} zaten var: GurOS bloğu sonuna eklenir (var olan metne dokunulmaz)",
               lambda: yaz(yol, mevcut.rstrip("\n") + "\n\n" + metin), isaret="~")


# ---------------------------------------------------------------- Claude Code ayarları
def _kanca_metni(h):
    return " ".join([str(h.get("command", "")), *(str(x) for x in (h.get("args") or []))]).replace("\\", "/")


def _bizim_kanca(h):
    return "/.claude/guros/kancalar.py" in _kanca_metni(h)


def _kanca(vault, alt, sure, python):
    # exec form: no shell in between, so it works the same under Git Bash, PowerShell, zsh and paths with spaces
    return {"type": "command", "command": python,
            "args": [(vault / ".claude" / "guros" / "kancalar.py").as_posix(), alt], "timeout": sure}


def izin_kurallari(ay, py):
    """Allow rules: GurOS's own scripts and the assistant's memory folder need no approval each time.

    Script names are spelled out (no '.claude/guros/*'), so an allowed command can never point at another file."""
    kurallar = []
    for b in IZINLI_BETIKLER:
        kurallar += [f"Bash({py} .claude/guros/{b}.py *)", f"PowerShell({py} .claude/guros/{b}.py *)"]
    kurallar.append(f"Edit(./{ay['hafiza_klasoru']}/**)")
    return kurallar


def _bizim_izin(kural, hafiza_klasorleri):
    return ".claude/guros/" in kural or any(kural == f"Edit(./{h}/**)" for h in hafiza_klasorleri)


def _ret_kurallari(ozel):
    return [f"Read(./{ozel}/**)", f"Edit(./{ozel}/**)"]


def _ayarlari_oku(yol):
    try:
        return json.loads(oku(yol)) if yol.exists() else {}
    except ValueError:
        raise RuntimeError(".claude/settings.json geçerli JSON değil; dosyadaki yazım hatasını düzeltip yeniden dene "
                           "(dosyaya dokunulmadı).")


def _ayarlari_birlestir(vault, ay, eski, py):
    yol = vault / ".claude" / "settings.json"
    veri = _ayarlari_oku(yol)
    if yol.exists():
        shutil.copy2(yol, yol.with_name(f"settings.json.yedek-{dt.datetime.now():%Y%m%d-%H%M%S}"))
        for fazla in sorted(yol.parent.glob("settings.json.yedek-*"))[:-3]:     # keep the three newest backups
            fazla.unlink()
    kancalar = veri.setdefault("hooks", {})
    python = hook_python()
    for olay, alt, eslesme, sure in KANCALAR:
        gruplar = [g for g in kancalar.get(olay, []) if not any(_bizim_kanca(h) for h in g.get("hooks", []))]
        grup = {"hooks": [_kanca(vault, alt, sure, python)]}
        if eslesme:
            grup = {"matcher": eslesme, **grup}
        kancalar[olay] = gruplar + [grup]

    izin = veri.setdefault("permissions", {})
    eski_ozel = set((eski or {}).get("ozel_klasorler", [])) - set(ay["ozel_klasorler"])
    # Claude Code consults only Read and Edit path rules (Read covers Grep/Glob, Edit covers Write);
    # Write/Glob/Grep path rules are ignored with a startup warning, so earlier versions' copies are dropped
    eskimis = {f"{a}(./{o}/**)" for o in set(ay["ozel_klasorler"]) | eski_ozel for a in ("Write", "Glob", "Grep")}
    eskimis |= {k for o in eski_ozel for k in _ret_kurallari(o)}
    ret = [k for k in izin.get("deny", []) if k not in eskimis]
    for o in ay["ozel_klasorler"]:
        ret += [k for k in _ret_kurallari(o) if k not in ret]
    izin["deny"] = ret
    hafizalar = {ay["hafiza_klasoru"], (eski or {}).get("hafiza_klasoru", ay["hafiza_klasoru"])}
    serbest = [k for k in izin.get("allow", []) if not _bizim_izin(k, hafizalar)]
    izin["allow"] = serbest + [k for k in izin_kurallari(ay, py) if k not in serbest]
    yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------- bakım zamanlaması
def _gorev_adi(vault):
    return "GurOS Bakim - " + re.sub(r"[^A-Za-z0-9 _-]+", "", vault.name)[:40]


def _zamanla(vault, saat):
    betik = vault / ".claude" / "guros" / "bakim.py"
    if os.name == "nt":
        pyw = Path(sys.executable).with_name("pythonw.exe")
        calistir = pyw if pyw.exists() else Path(sys.executable)
        subprocess.run(["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", saat, "/TN", _gorev_adi(vault),
                        "/TR", f'"{calistir}" "{betik}"'], check=True, capture_output=True)
    else:
        satir = f'{int(saat.split(":")[1])} {int(saat.split(":")[0])} * * * "{sys.executable}" "{betik}" >/dev/null 2>&1  # GurOS'
        eski = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
        if str(betik) not in eski:
            subprocess.run(["crontab", "-"], input=eski.rstrip("\n") + ("\n" if eski.strip() else "") + satir + "\n",
                           text=True, check=True)


def _zamanlamayi_kaldir(vault):
    if os.name == "nt":
        subprocess.run(["schtasks", "/Delete", "/F", "/TN", _gorev_adi(vault)], capture_output=True)
        return
    betik = str(vault / ".claude" / "guros" / "bakim.py")
    try:
        eski = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    except OSError:
        return
    if betik in eski:
        kalan = "".join(s for s in eski.splitlines(True) if betik not in s)
        subprocess.run(["crontab", "-"], input=kalan, text=True, check=True)


# ---------------------------------------------------------------- kaldırma
def kaldir_plani(vault):
    vault = Path(vault).expanduser().resolve()
    p = Plan("GurOS kaldırma", vault)
    ay = kurulu_ayarlar(vault) or {}
    if not ay and not (vault / ".claude" / "settings.json").exists():
        p.bilgi("bu vault'ta GurOS kurulu görünmüyor")
    yol = vault / ".claude" / "settings.json"
    if yol.exists():
        def temizle():
            veri = _ayarlari_oku(yol)
            for olay in list(veri.get("hooks", {})):
                veri["hooks"][olay] = [g for g in veri["hooks"][olay] if not any(_bizim_kanca(h) for h in g.get("hooks", []))]
                if not veri["hooks"][olay]:
                    del veri["hooks"][olay]
            if not veri.get("hooks"):
                veri.pop("hooks", None)
            izin = veri.get("permissions", {})
            if "allow" in izin:
                izin["allow"] = [k for k in izin["allow"] if not _bizim_izin(k, {ay.get("hafiza_klasoru", "🔮 Logos")})]
                if not izin["allow"]:
                    del izin["allow"]
            yaz(yol, json.dumps(veri, ensure_ascii=False, indent=2) + "\n")
        p.adim("Claude Code", ".claude/settings.json — kancalar ve GurOS izinleri çıkar (gizlilik kuralları koruma için kalır)",
               temizle, isaret="-")
    komutlar = sorted(k for k in (vault / ".claude" / "commands").glob("*.md") if (SABLON / "komutlar" / k.name).exists())
    if komutlar:
        p.adim("Claude Code", f"{len(komutlar)} komut: " + " ".join("/" + k.stem for k in komutlar),
               lambda: [k.unlink() for k in komutlar], isaret="-")
    for ad in ("CLAUDE.md", "CLAUDE.guros.md", "AGENTS.md"):
        dosya = vault / ad
        metin = oku(dosya)
        if ISARET_BAS in metin and ISARET_SON in metin:
            kalan = metin[:metin.index(ISARET_BAS)] + metin[metin.index(ISARET_SON) + len(ISARET_SON):]
            kalan = kalan.strip()
            p.adim("Asistan kuralları", f"{ad} — GurOS bloğu çıkar" + (" (başka metin olmadığı için dosya silinir)" if not kalan
                   else " (blok dışındaki metnine dokunulmaz)"),
                   (lambda f=dosya: f.unlink()) if not kalan else (lambda f=dosya, k=kalan: yaz(f, k + "\n")), isaret="-")
    claude = vault / "CLAUDE.md"
    if "@CLAUDE.guros.md" in oku(claude) and (vault / "CLAUDE.guros.md").exists():
        p.adim("Asistan kuralları", "CLAUDE.md — '@CLAUDE.guros.md' satırı çıkar",
               lambda: yaz(claude, re.sub(r"\n*@CLAUDE\.guros\.md\n?", "\n", oku(claude)).rstrip("\n") + "\n"), isaret="-")
    if (vault / ".claude" / "guros").exists():
        p.adim("Sistem", ".claude/guros/ — sistem kodu silinir", lambda: shutil.rmtree(vault / ".claude" / "guros"), isaret="-")
        p.adim("Bakım", "varsa günlük bakım görevi kaldırılır", lambda: _zamanlamayi_kaldir(vault), isaret="-")
    p.bilgi("notların, hafıza klasörün ve özel klasörlerin yerinde kalır")
    return p


# ---------------------------------------------------------------- doğrulama ve sonraki adımlar
def dogrula(vault):
    print(f"\n  🩺 {R.kalin('Sağlık kontrolü')}")
    ortam = dict(os.environ, GUROS_VAULT=str(vault), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(vault / ".claude" / "guros" / "doktor.py")], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ortam)
    for satir in r.stdout.strip().splitlines()[1:]:
        satir = satir.strip()
        if not satir:
            continue
        if satir.startswith("✓"):
            satir = R.yesil("✓") + satir[1:]
        elif satir.startswith("✗"):
            satir = R.kirmizi("✗") + satir[1:]
        elif satir.startswith("⚠"):
            satir = R.sari("⚠") + satir[1:]
        print("     " + satir)
    if r.returncode != 0 and r.stderr.strip():
        print("     " + R.kirmizi(r.stderr.strip().splitlines()[-1]))
    return r.returncode


def _cd_komutu(vault):
    return f'cd "{vault}"' if os.name == "nt" else f"cd {shlex.quote(str(vault))}"


def claude_kurulum_komutu():
    if os.name == "nt":
        return "irm https://claude.ai/install.ps1 | iex", "PowerShell"
    return "curl -fsSL https://claude.ai/install.sh | bash", "Terminal"


def terminal_ac(vault):
    """Open a new terminal window in the vault with Claude Code running. False if no terminal could be opened."""
    try:
        if os.name == "nt":
            if shutil.which("wt"):
                subprocess.Popen(["wt", "-d", str(vault), "cmd", "/k", "claude"])
            else:
                subprocess.Popen(f'start "GurOS" /D "{vault}" cmd /k claude', shell=True)
            return True
        if sys.platform == "darwin":
            komut = f"cd {shlex.quote(str(vault))} && claude".replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(["osascript", "-e", f'tell application "Terminal" to do script "{komut}"',
                            "-e", 'tell application "Terminal" to activate'], check=True, capture_output=True, timeout=30)
            return True
        for komut in (["gnome-terminal", f"--working-directory={vault}", "--", "claude"],
                      ["konsole", "--workdir", str(vault), "-e", "claude"],
                      ["x-terminal-emulator", "-e", "claude"]):
            if shutil.which(komut[0]):
                subprocess.Popen(komut, cwd=str(vault))
                return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def sonraki_adimlar(vault, ay, sihirbaz=False, guncelleme=False):
    a = ay or {}
    asistan = a.get("asistan", "Logos")
    print(f"\n  {R.yesil(R.kalin('✔ Güncelleme tamam.' if guncelleme else '✔ Kurulum tamam.'))}\n")
    print(f"  {R.kalin('Sıradaki adımlar')}")
    print(f"   {R.mor('1')}  {R.kalin('Obsidian')}     \"Open folder as vault\" ile bu klasörü aç: {vault}")
    print(f"   {R.mor('2')}  {R.kalin('Claude Code')}  Bir terminalde vault'a geçip başlat:")
    print(f"                     {R.mavi(_cd_komutu(vault))}")
    print(f"                     {R.mavi('claude')}")
    print(f"                  İlk açılışta \"Do you trust the files in this folder?\" sorusuna {R.kalin('Yes')} de;")
    print("                  hafıza ve gizlilik koruması ancak o zaman çalışır.")
    print(f"   {R.mor('3')}  {R.kalin('Merhaba de')}   {asistan} kendini tanıtır ve seni tanımak için birkaç soru sorar.")
    print(R.soluk("\n   Codex kullanıyorsan aynı klasörde codex başlat; kuralları AGENTS.md'den okur."))
    print(R.soluk(f"   Nasıl kullanılır: vault'taki \"👋 Başlarken\" notu. Yedek (isteğe bağlı): {py_kisa()} .claude/guros/yedek.py --kur <ÖZEL repo>"))
    if not claude_yolu():
        komut, kabuk = claude_kurulum_komutu()
        print(f"\n  {R.sari('!')} Claude Code bu bilgisayarda yok. Kurmak için {kabuk}'e yapıştır (ücretli bir Claude hesabı gerekir):")
        print(f"     {R.mavi(komut)}")
        return
    if sihirbaz and _evet("Claude Code'u şimdi bu vault'ta yeni bir pencerede açayım mı?", True):
        if terminal_ac(vault):
            print(f"  {R.yesil('✓')} Yeni pencerede açıldı. Güven sorusuna Yes de, sonra \"merhaba\" yaz.")
        else:
            print(f"  Pencere açılamadı; kendin aç:  {_cd_komutu(vault)}  ve  claude")


# ---------------------------------------------------------------- sihirbaz
def _girdi(soru):
    try:
        return input(soru).strip()
    except (EOFError, KeyboardInterrupt):
        raise Iptal()


def _evet(soru, varsayilan):
    ek = "[E/h]" if varsayilan else "[e/H]"
    while True:
        c = _girdi(f"\n  {R.kalin('?')} {soru} {R.soluk(ek)} ").lower()
        if not c:
            return varsayilan
        if c in ("e", "evet", "y", "yes", "ok", "tamam"):
            return True
        if c in ("h", "hayır", "hayir", "n", "no"):
            return False


def _sor(soru, varsayilan=None):
    ek = f" {R.soluk('[' + varsayilan + ']')}" if varsayilan else ""
    while True:
        c = _girdi(f"     {soru}{ek}: ")
        if c:
            return c
        if varsayilan is not None:
            return varsayilan


def _yeni_vault_yolu():
    ev = Path.home()
    for aday in (ev / "Documents", ev / "Belgeler", ev / "OneDrive" / "Documents", ev / "OneDrive" / "Belgeler"):
        if aday.is_dir():
            return aday / "GurOS"
    return ev / "GurOS"


def _vault_sor():
    print(f"\n  {R.mor('①')} {R.kalin('Vault nerede?')}")
    vaultlar = [v for v in obsidian_vaultlari() if not _icinde(v[1], DEPO)][:9]
    yeni = _yeni_vault_yolu()
    if vaultlar:
        print("     Bilgisayarında bulduğum Obsidian vault'ları:")
        genislik = max(len(ad) for ad, _ in vaultlar)
        for i, (ad, yol) in enumerate(vaultlar, 1):
            print(f"       {R.mor(str(i))}) {ad.ljust(genislik)}  {R.soluk(str(yol))}")
        print(f"       {R.mor(str(len(vaultlar) + 1))}) {'Yeni vault'.ljust(genislik)}  {R.soluk(str(yeni))}")
    else:
        print(f"     Obsidian vault'u bulamadım; yeni bir tane açacağım: {R.soluk(str(yeni))}")
    print(R.soluk("     (Başka bir klasör için yolunu yapıştır.)"))
    varsayilan = "1" if vaultlar else str(yeni)
    while True:
        c = _sor("Seçimin", varsayilan).strip().strip("\"'")
        if c.isdigit() and vaultlar and 1 <= int(c) <= len(vaultlar) + 1:
            return vaultlar[int(c) - 1][1] if int(c) <= len(vaultlar) else yeni
        yol = Path(os.path.expandvars(os.path.expanduser(c)))
        if not yol.is_absolute():
            print(R.sari("     Tam yol yaz (ör. C:\\Users\\sen\\Documents\\Vault ya da ~/Documents/Vault)."))
            continue
        yol = yol.resolve()
        if yol.exists() and not yol.is_dir():
            print(R.sari("     Bu bir dosya; bir klasör yolu yaz."))
        elif _icinde(yol, DEPO) or _icinde(DEPO, yol):
            print(R.sari("     Bu, kurulum paketinin klasörü; vault başka bir yerde olmalı."))
        else:
            return yol


def _ozel_sor(vault, hafiza):
    print(f"\n  {R.mor('④')} {R.kalin('Yapay zekâya kapalı klasörler')}")
    ozel = []
    adaylar = ozel_adaylar(vault, haric={hafiza})
    if adaylar:
        print("     Vault'unda adından özel olduğu anlaşılan klasörler var (içlerine bakmadım):")
        for a in adaylar:
            print(f"       🔒 {a}")
        if _evet("Bunlar yapay zekâya kapalı kalsın mı?", True):
            ozel += adaylar
    print("     Günlük, sağlık kaydı gibi şeyler için ayrıca bir özel klasör açılacak.")
    ozel.insert(0, _sor("Özel klasörün adı", VARSAYILAN_OZEL))
    while True:
        ek = _girdi(f"     Kapalı kalacak başka bir klasör {R.soluk('(adını yaz, yoksa Enter)')}: ").strip().strip("\"'/\\")
        if not ek:
            return list(dict.fromkeys(ozel))
        ozel.append(ek)


def sihirbaz():
    _baslik()
    print(f"  Birkaç soru soracağım. {R.kalin('Sen onaylamadan hiçbir şey yazılmaz.')} {R.soluk('(Çıkmak için Ctrl+C)')}")
    vault = _vault_sor()
    mevcut = kurulu_ayarlar(vault)
    s = {}
    if mevcut is not None:
        print(f"\n     Bu vault'ta GurOS {mevcut.get('surum', '?')} zaten kurulu ({mevcut.get('ad', '?')} için).")
        print(f"       {R.mor('1')}) Güncelle  {R.soluk('sistem ve kurallar yenilenir, notlarına ve hafızana dokunulmaz')}")
        print(f"       {R.mor('2')}) Kaldır    {R.soluk('kancalar ve sistem kodu silinir, notların kalır')}")
        print(f"       {R.mor('3')}) Vazgeç")
        secim = _sor("Seçimin", "1")
        if secim == "3":
            print("\n  Tamam, hiçbir şey değişmedi.")
            return 0
        if secim == "2":
            p = kaldir_plani(vault)
            p.goster()
            if not _evet("Kaldırayım mı?", False):
                print("\n  Tamam, hiçbir şey değişmedi.")
                return 0
            ok = p.uygula()
            print(f"\n  {R.yesil('✔ GurOS kaldırıldı.') if ok else R.kirmizi('Kaldırma yarıda kaldı.')}")
            return 0 if ok else 1
    else:
        print(f"\n  {R.mor('②')} {R.kalin('Sana nasıl hitap edeyim?')}")
        s["ad"] = _sor("Adın")
        print(f"\n  {R.mor('③')} {R.kalin('Asistanının adı ne olsun?')}")
        s["asistan"] = _sor("Asistan", "Logos")
        s["ozel"] = _ozel_sor(vault, "🔮 Logos")
    p, ay = kur_plani(vault, s)
    p.goster()
    if p.sorunlar:
        return 1
    if not _evet("Kurayım mı?" if mevcut is None else "Güncelleyeyim mi?", True):
        print("\n  Tamam, hiçbir şey yazılmadı.")
        return 0
    if not p.uygula():
        return 1
    kod = dogrula(vault)
    sonraki_adimlar(vault, ay, sihirbaz=True, guncelleme=mevcut is not None)
    return kod


# ---------------------------------------------------------------- giriş
def _etkilesimli():
    if os.environ.get("GUROS_SIHIRBAZ") == "1":
        return True
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def main(argv):
    ap = argparse.ArgumentParser(description="GurOS kurulumu", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--vault")
    ap.add_argument("--ad")
    ap.add_argument("--asistan")
    ap.add_argument("--hafiza")
    ap.add_argument("--proje")
    ap.add_argument("--ozel", action="append")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--kaldir", action="store_true")
    ap.add_argument("--zamanla", action="store_true")
    ap.add_argument("--saat", default="10:00")
    ap.add_argument("--vaultlar", action="store_true", help="bu bilgisayardaki Obsidian vault'larını listele")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"\d{1,2}:\d{2}", a.saat):
        ap.error("--saat SS:DD biçiminde olmalı")
    if a.vaultlar:
        vaultlar = obsidian_vaultlari()
        for ad, yol in vaultlar:
            print(f"{ad}\t{yol}")
        if not vaultlar:
            print("Obsidian vault'u bulunamadı.")
        return 0
    if not a.vault:
        if not _etkilesimli():
            print("--vault gerekli. Soru soran kurulum bir terminal ister; terminalde argümansız çalıştır:\n"
                  "    python kur.py\n"
                  "Ya da her şeyi bayraklarla ver (önce plan, sonra --uygula):\n"
                  "    python kur.py --vault \"<vault klasörü>\" --ad \"<adın>\" [--ozel \"<özel klasör>\"] [--uygula]",
                  file=sys.stderr)
            return 2
        try:
            return sihirbaz()
        except Iptal:
            print(f"\n\n  {R.sari('İptal edildi.')} Onaylanmış bir adım yoksa hiçbir şey yazılmadı.")
            return 130

    vault = Path(a.vault).expanduser().resolve()
    if a.kaldir:
        p, ay = kaldir_plani(vault), None
    else:
        p, ay = kur_plani(vault, {"ad": a.ad, "asistan": a.asistan, "hafiza": a.hafiza, "proje": a.proje,
                                  "ozel": a.ozel, "zamanla": a.zamanla, "saat": a.saat})
    if p.sorunlar or not a.uygula:
        p.goster()
        if not p.sorunlar:
            print(f"\n  Uygulamak için aynı komutu {R.kalin('--uygula')} ile çalıştır.")
        return 1 if p.sorunlar else 0
    if not p.uygula():
        return 1
    if a.kaldir:
        print(f"\n  {R.yesil('✔ GurOS kaldırıldı.')}")
        return 0
    guncelleme = any("zaten kurulu" in b for b in p.bilgiler)
    kod = dogrula(vault)
    sonraki_adimlar(vault, ay, guncelleme=guncelleme)
    return kod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
