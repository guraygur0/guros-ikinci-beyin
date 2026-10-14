"""Claude Code hooks for GurOS. One entry point, one sub-command per event:

    oturum     SessionStart      opening context (goals, projects, threads, last session)
    istem      UserPromptSubmit  count prompts, add Recall pointers, nudge in long sessions
    dur        Stop              memory freshness: after N prompts without a memory write, ask for one
    sikistir   PreCompact        make sure the next Stop asks for a memory write before details are summarised away
    koruma     PreToolUse        block any tool call that touches a private folder

A hook that crashes must not lock the user out, so every handler fails open (exit 0) and reports on stderr —
except the privacy guard, whose whole job is to say no.
"""
import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

HATIRLATMA_ARALIGI = 15


def _sayac_yolu():
    return ortak.durum_dizini() / "sayac.json"


def _sayac():
    try:
        return json.loads(ortak.oku(_sayac_yolu()) or "{}")
    except ValueError:
        return {}


def _sayac_yaz(veri):
    ortak.guvenli_yaz(_sayac_yolu(), json.dumps(veri))


def _hafiza_damgasi():
    """Newest modification time of any file in the memory folder (0 if it does not exist)."""
    en = 0
    kok = ortak.hafiza_dizini()
    for yol, _, dosyalar in os.walk(kok):
        for ad in dosyalar:
            try:
                en = max(en, os.stat(os.path.join(yol, ad)).st_mtime_ns)
            except OSError:
                pass
    return en


def oturum():
    import baglam
    import recall
    ortak.hook_girdisi()
    try:
        recall.indeks()               # incremental: only notes changed since last time are re-read
    except Exception as e:
        print(f"Recall indeksi güncellenemedi: {e}", file=sys.stderr)
    s = _sayac()
    s.update({"istem": 0, "son_yazim_istem": 0, "hafiza_damgasi": _hafiza_damgasi(), "zorla": False})
    _sayac_yaz(s)
    ortak.hook_baglami("SessionStart", baglam.ozet())


def istem():
    import recall
    girdi = ortak.hook_girdisi()
    s = _sayac()
    s["istem"] = s.get("istem", 0) + 1
    _sayac_yaz(s)
    parcalar = []
    if s["istem"] >= HATIRLATMA_ARALIGI and s["istem"] % HATIRLATMA_ARALIGI == 0:
        parcalar.append(f"[GurOS] Oturum uzadı ({s['istem']} mesaj). Bitirirken Last-Session.md ve Threads.md'yi güncelle.")
    isaret = recall.isaretciler(girdi.get("prompt", ""))
    if isaret:
        parcalar.append(isaret)
    ortak.hook_baglami("UserPromptSubmit", "\n\n".join(parcalar))


def dur():
    girdi = ortak.hook_girdisi()
    if girdi.get("stop_hook_active"):
        return                                         # never block the continuation we caused ourselves
    ay = ortak.ayarlar()
    s = _sayac()
    damga = _hafiza_damgasi()
    if damga > s.get("hafiza_damgasi", 0):
        s.update({"hafiza_damgasi": damga, "son_yazim_istem": s.get("istem", 0), "zorla": False})
        _sayac_yaz(s)
        return
    bekleyen = s.get("istem", 0) - s.get("son_yazim_istem", 0)
    if bekleyen < ay.get("hatirlatma_esigi", 10) and not s.get("zorla"):
        return
    s.update({"son_yazim_istem": s.get("istem", 0), "zorla": False})
    _sayac_yaz(s)
    neden = (f"[GurOS] {bekleyen} mesajdır hafızaya ({ay['hafiza_klasoru']}/) yazılmadı"
             + (" ve bağlam sıkıştırıldı" if bekleyen < ay.get("hatirlatma_esigi", 10) else "") + ". "
             "Bu oturumda yeni bir bilgi, karar ya da biten iş doğduysa şimdi yaz: kişi hakkında yeni bilgi Facts.md'ye, "
             "süren iş Threads.md'ye, alınan karar 📌 Kararlar.md'ye, oturum özeti Session-Handoffs/ içine. "
             "Yazacak yeni bir şey yoksa Journal.md'ye tek satır not düş ve devam et.")
    print(json.dumps({"decision": "block", "reason": neden}, ensure_ascii=False))


def sikistir():
    ortak.hook_girdisi()
    s = _sayac()
    s["zorla"] = True
    _sayac_yaz(s)


def koruma():
    """Exit 2 (blocked) when a tool call reaches into a private folder; the reason goes back to the assistant."""
    girdi = ortak.hook_girdisi()
    ay = ortak.ayarlar()
    arac_adi = girdi.get("tool_name", "")
    arac = girdi.get("tool_input") or {}
    vault = ortak.vault_kok().resolve()
    cwd = _mutlak(str(girdi.get("cwd") or os.getcwd()), Path.cwd())
    hedefler = [_mutlak(k, vault) for k in ay.get("ozel_klasorler", [])]
    for k in ("file_path", "path", "notebook_path"):
        yol = arac.get(k)
        if isinstance(yol, str) and yol and any(_icinde(_mutlak(yol, cwd), h) for h in hedefler):
            return _engelle(ay, yol)
    # Shell commands and search patterns: false positives are cheap (rephrase the command), a leaked diary is not.
    metinler = [str(v) for k, v in arac.items() if isinstance(v, (str, int)) and k not in ("content", "new_string", "old_string")]
    klasor = ortak.ozel_anilir(" ".join(metinler), ay)
    if klasor:
        return _engelle(ay, klasor)
    # A search that sweeps a parent folder walks into the private one without ever naming it.
    neden = _genis_erisim(arac_adi, arac, cwd, hedefler)
    if neden:
        print(f"[GurOS gizlilik] {neden} Bu yüzden özel alana da girer. Aramayı bir alt klasöre daralt "
              "(ör. path=\"Projeler\" ya da grep -r kelime Projeler) veya vault genelinde Recall kullan: "
              "python .claude/guros/recall.py ara \"<konu>\" (özel alan indekste yoktur).", file=sys.stderr)
        return 2
    return 0


_JOKER = re.compile(r"[*?\[{]")
_SARMALAYICI = {"sudo", "xargs", "timeout", "time", "nice", "nohup", "command", "builtin", "env", "stdbuf", "noglob", "&", "."}
_DESEN_ONCE = {"grep", "egrep", "fgrep", "zgrep", "rg", "ag", "ack", "findstr"}       # first plain word is the pattern
_HEP_OZYINELI = {"rg", "ag", "ack", "find", "fd", "fdfind", "tree", "du", "rsync", "tar", "zip", "7z",
                 "robocopy", "xcopy", "compress-archive"}
_LISTELER = {"ls", "dir", "gci", "get-childitem", "tree", "du", "find", "stat"}       # naming a folder shows its contents


def _mutlak(metin, cwd):
    """Absolute form of a path as the tool would see it: relative paths start at the session folder."""
    s = metin.strip().strip("\"'")
    s = re.sub(r"^\$\{?pwd\}?", lambda m: str(cwd).replace("\\", "/"), s, flags=re.I)
    if os.name == "nt":
        s = re.sub(r"^/([a-zA-Z])(/|$)", lambda m: m.group(1) + ":/", s)        # Git Bash: /c/Users -> c:/Users
    p = Path(os.path.expanduser(os.path.expandvars(s)))
    if not p.is_absolute():
        p = Path(cwd) / p
    try:
        return p.resolve()
    except (OSError, RuntimeError, ValueError):
        return Path(os.path.abspath(str(p)))


def _icinde(yol, hedef):
    return yol == hedef or hedef in yol.parents


def _kapsar(taban, hedefler):
    """True if a recursive walk from `taban` reaches a private folder (it is the folder, inside it, or above it)."""
    return any(_icinde(taban, h) or taban in h.parents for h in hedefler)


def _ulasir(desen, taban, hedefler, ici):
    """True if a wildcard pattern, read from `taban`, can match a private folder (ici=True: something inside it)."""
    m = _JOKER.search(desen)
    if not m:
        return False                               # a literal path was already checked by name
    kes = max(desen.rfind("/", 0, m.start()), desen.rfind("\\", 0, m.start()))
    on = desen[:kes] if kes > 0 else desen[:1] if kes == 0 else ""
    yer = _mutlak(on, taban) if on else taban
    kalan = [p for p in re.split(r"[/\\]+", desen[kes + 1:]) if p and p != "."]
    for h in hedefler:
        if _icinde(yer, h):
            return True
        try:
            gerek = h.relative_to(yer).parts
        except ValueError:
            continue
        for i, parca in enumerate(kalan):
            if parca == "**" or i >= len(gerek):
                return True
            desen_ = re.sub(r"\{[^}]*\}", "*", ortak.katla(parca))
            if not fnmatch.fnmatchcase(ortak.katla(gerek[i]), desen_):
                break
        else:
            if len(kalan) > len(gerek) or (len(kalan) == len(gerek) and not ici):
                return True
    return False


def _dar_ad(desen):
    """A Glob whose file-name part has a real word in it ('**/*Interstellar*') returns only those names."""
    son = re.split(r"[/\\]", desen)[-1]
    son = re.sub(r"\.[A-Za-z0-9]{1,5}$", "", son)
    return len(re.sub(r"\{[^}]*\}|\[[^\]]*\]|[*?]", "", son)) >= 3


def _ogeler(parca, ps):
    try:
        ogeler = shlex.split(parca, posix=not ps)
    except ValueError:
        ogeler = parca.split()
    return [o.strip("\"'") if ps else o for o in ogeler]


def _ozyineli(komut, ogeler, bayraklar, ps):
    if komut in _HEP_OZYINELI:
        return True
    if komut in ("grep", "egrep", "fgrep", "zgrep"):
        return any(re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", b) or b.startswith(("--recursive", "--dereference-recursive",
                                                                                  "--directories=recurse"))
                   for b in bayraklar)
    if komut == "git":
        return len(ogeler) > 1 and ogeler[1] == "grep"
    if ps and komut in ("ls", "dir", "gci", "get-childitem", "cp", "cpi", "copy", "copy-item", "select-string", "sls"):
        return any(b.lower().startswith(("-r", "-de")) for b in bayraklar)
    if komut in ("cp", "scp"):
        return any(re.fullmatch(r"-[a-zA-Z]*[rRa][a-zA-Z]*", b) or b in ("--recursive", "--archive") for b in bayraklar)
    if komut == "ls":
        return any(re.fullmatch(r"-[a-zA-Z]*R[a-zA-Z]*", b) or b == "--recursive" for b in bayraklar)
    if komut in ("findstr", "dir"):
        return any(b.lower() == "/s" for b in bayraklar)
    return False


def _genis_erisim(arac_adi, arac, cwd, hedefler):
    """Why a call would sweep a private folder without naming it ('' if it would not)."""
    if not hedefler:
        return ""
    if arac_adi == "Grep":
        taban = _mutlak(str(arac.get("path") or "."), cwd)
        if not _kapsar(taban, hedefler):
            return ""
        g = str(arac.get("glob") or "")
        if g and ("/" in g or "\\" in g) and not g.startswith("!") and not arac.get("type") \
                and not _ulasir(g, taban, hedefler, ici=True) and _JOKER.search(g):
            return ""                              # the glob pins the search to folders outside the private one
        return f"Grep, özel klasörün üstündeki bir klasörü ({taban.name or taban}) baştan sona tarıyor."
    if arac_adi == "Glob":
        taban = _mutlak(str(arac.get("path") or "."), cwd)
        desen = str(arac.get("pattern") or "")
        if _ulasir(desen, taban, hedefler, ici=True) and not _dar_ad(desen):
            return f"Bu Glob deseni ({desen}) özel klasördeki dosya adlarını da listeler."
        return ""
    if arac_adi not in ("Bash", "PowerShell"):
        return ""
    ps = arac_adi == "PowerShell"
    yer = cwd
    for parca in re.split(r"&&|\|\||[;|\n]", str(arac.get("command", ""))):
        ogeler = _ogeler(parca, ps)
        while ogeler and (ogeler[0].lower() in _SARMALAYICI or re.fullmatch(r"\d+[smhd]?", ogeler[0])
                          or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", ogeler[0])):
            ogeler = ogeler[1:]
        if not ogeler:
            continue
        komut = re.sub(r"\.exe$", "", os.path.basename(ogeler[0]).lower())
        if komut in ("cd", "set-location", "sl", "pushd", "chdir") and len(ogeler) > 1:
            yer = _mutlak(ogeler[-1], yer)
            continue
        egik_bayrak = komut in ("findstr", "dir") and not ps
        bayraklar = [o for o in ogeler[1:] if o.startswith("-") or (egik_bayrak and re.fullmatch(r"/[A-Za-z?](:.*)?", o))]
        yollar = [o for o in ogeler[1:] if o not in bayraklar]
        if komut == "git":
            yollar = yollar[1:]                                     # "grep"
        desen = yollar[0] if yollar and (komut in _DESEN_ONCE or komut == "git") else None
        if desen is not None:
            yollar = yollar[1:]
        ozyineli = _ozyineli(komut, ogeler, bayraklar, ps)
        for o in yollar:
            if _ulasir(o, yer, hedefler, ici=not (ozyineli or komut in _LISTELER)):
                return f"Bu komuttaki joker ({o}) özel klasöre genişler."
        if ozyineli:
            # flag values (-Filter *.md, -g "*.md") look like paths; without a real folder argument the walk starts here
            if not any(_mutlak(y, yer).is_dir() for y in yollar):
                yollar = yollar + ["."]
            for y in yollar:
                if _kapsar(_mutlak(y, yer), hedefler):
                    return f"Bu komut ({komut}) özel klasörün üstündeki bir klasörü özyinelemeli tarıyor."
    return ""


def _engelle(ay, neyi):
    print(f"[GurOS gizlilik] Bu işlem özel alana dokunuyor ({neyi}). {ay['ad']} bu klasörü özel ilan etti: "
          "okunmaz, aranmaz, değiştirilmez. Bilgiye gerçekten ihtiyaç varsa kullanıcıdan kendisinin yapıştırmasını iste.",
          file=sys.stderr)
    return 2


OLAYLAR = {"oturum": oturum, "istem": istem, "dur": dur, "sikistir": sikistir, "koruma": koruma}


def main(argv):
    if not argv or argv[0] not in OLAYLAR:
        print("kullanım: kancalar.py " + "|".join(OLAYLAR), file=sys.stderr)
        return 0
    if argv[0] == "koruma":
        try:
            return OLAYLAR["koruma"]() or 0
        except Exception as e:                     # a broken guard is visible, but does not lock the session
            print(f"[GurOS] koruma kancası hata verdi: {e}", file=sys.stderr)
            return 1
    try:
        OLAYLAR[argv[0]]()
    except Exception as e:
        print(f"[GurOS] {argv[0]} kancası hata verdi: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
