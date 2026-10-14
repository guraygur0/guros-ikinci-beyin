"""Recall: local keyword search over the vault (BM25 + a Turkish/English synonym bridge).

    python recall.py ara uzay filmi        # search from the terminal
    python recall.py kur                   # rebuild the index
    python recall.py --hook                # UserPromptSubmit hook: stdin JSON -> pointers for the assistant

Nothing leaves the machine: no model, no network. Private folders are never indexed.
The index lives in the machine-local state folder and is refreshed incrementally (only changed files are re-read).
"""
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

SURUM = 3
ATLANAN = {".obsidian", ".trash", ".git", ".claude", ".github", "node_modules", "__pycache__"}
PROTOKOL_DOSYALARI = {"CLAUDE.md", "AGENTS.md", "CLAUDE.guros.md", "👋 Başlarken.md"}
DURAK = set("""ve ile bir bu su o da de mi mu ki en cok icin gibi daha ama veya ya ne nasil neden olan olarak
misin musun misiniz musunuz miyim muyum bana beni benim bende sen ben sana seni senin biz bize bizim onu ona onun
sey seyi seyler var yok nedir neler nerede hangi kim bi biraz lutfen tamam evet hayir simdi hep her hic
the a an and or of to in on for is are was were be it this that with as at by from how what why me my you your""".split())
PARCA = 1200           # characters per chunk before a long section is split
ESIK = 1.5             # minimum score before the hook shows a pointer; the matched-word gate does most of the work


_KOKLER = None


def _kokler():
    """The synonym dictionary doubles as a stem lexicon: 'filmler', 'filmi' and 'film' all meet at 'film'."""
    global _KOKLER
    if _KOKLER is None:
        _KOKLER = {k for k in es_anlamlar() if " " not in k and len(k) >= 3}
    return _KOKLER


def kelimeler(metin):
    kokler = _kokler()
    out = []
    for w in re.split(r"[^a-z0-9]+", ortak.katla(metin)):
        if len(w) < 2 or w in DURAK:
            continue
        out.append(w)
        if len(w) > 5:
            out.append(w[:5])          # crude Turkish stem: "projelerim" and "projeler" meet at "proje"
        if len(w) >= 4 and w.endswith("s") and not w.endswith("ss"):
            out.append(w[:-1])         # English plural: "notes" -> "note"
        if w not in kokler:
            kok = next((w[:n] for n in range(len(w) - 1, 2, -1) if w[:n] in kokler), None)
            if kok:
                out.append(kok)
    return out


def es_anlamlar():
    try:
        with io.open(ortak.KOD / "es_anlamlar.json", encoding="utf-8") as f:
            gruplar = json.load(f).get("gruplar", [])
    except (OSError, ValueError):
        return {}
    harita = {}
    for grup in gruplar:
        katli = [ortak.katla(g) for g in grup]
        for g in katli:
            harita.setdefault(g, set()).update(x for x in katli if x != g)
    return harita


def _kaynaklar(vault, ay):
    for kok, dizinler, dosyalar in os.walk(vault):
        goreli_kok = Path(kok).relative_to(vault)
        dizinler[:] = sorted(d for d in dizinler
                             if d not in ATLANAN and not d.startswith(".")
                             and not ortak.ozel_mi(goreli_kok / d, ay))
        for ad in sorted(dosyalar):
            if goreli_kok == Path(".") and ad in PROTOKOL_DOSYALARI:
                continue                    # protocol and welcome note mention every topic; indexed, they would answer every query
            if ad.lower().endswith(".md") and not ortak.ozel_mi(goreli_kok / ad, ay):
                yield (goreli_kok / ad).as_posix()


def _parcala(metin):
    """Split a note into (heading, text) sections; long sections are cut on paragraph boundaries."""
    metin = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", metin, flags=re.S)       # frontmatter is metadata, not content
    bolumler, baslik, tampon = [], "", []
    for satir in metin.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)", satir)
        if m:
            if "".join(tampon).strip():
                bolumler.append((baslik, "\n".join(tampon)))
            baslik, tampon = m.group(2).strip(), []
        else:
            tampon.append(satir)
    if "".join(tampon).strip():
        bolumler.append((baslik, "\n".join(tampon)))
    out = []
    for baslik, govde in bolumler:
        parca = ""
        for paragraf in re.split(r"\n\s*\n", govde):
            if parca and len(parca) + len(paragraf) > PARCA:
                out.append((baslik, parca.strip()))
                parca = ""
            parca += paragraf + "\n\n"
        if parca.strip():
            out.append((baslik, parca.strip()))
    return out


def indeks(vault=None, zorla=False):
    """Load the index, re-reading only notes whose size or modification time changed."""
    vault = Path(vault) if vault else ortak.vault_kok()
    ay = ortak.ayarlar(vault)
    yol = ortak.durum_dizini(vault) / "recall.json"
    eski = {}
    if not zorla:
        try:
            with io.open(yol, encoding="utf-8") as f:
                eski = json.load(f)
            if eski.get("v") != SURUM:
                eski = {}
        except (OSError, ValueError):
            eski = {}
    eski_dosyalar = eski.get("dosyalar", {})
    yeni, degisti = {}, False
    for goreli in _kaynaklar(vault, ay):
        try:
            st = (vault / goreli).stat()
        except OSError:
            continue
        damga = [st.st_mtime_ns, st.st_size]
        onceki = eski_dosyalar.get(goreli)
        if onceki and onceki.get("damga") == damga:
            yeni[goreli] = onceki
            continue
        degisti = True
        parcalar = []
        for baslik, govde in _parcala(ortak.oku(vault / goreli)):
            parcalar.append({"b": baslik, "m": govde[:600], "t": kelimeler(" ".join([Path(goreli).stem, *Path(goreli).parent.parts, baslik, govde]))})
        yeni[goreli] = {"damga": damga, "p": parcalar}
    if set(yeni) != set(eski_dosyalar):
        degisti = True
    if degisti or not eski:
        df, toplam, n = {}, 0, 0
        for kayit in yeni.values():
            for p in kayit["p"]:
                for w in set(p["t"]):
                    df[w] = df.get(w, 0) + 1
                toplam += len(p["t"])
                n += 1
        veri = {"v": SURUM, "dosyalar": yeni, "df": df, "n": n, "avgdl": (toplam / n) if n else 1.0}
        ortak.guvenli_yaz(yol, json.dumps(veri, ensure_ascii=False))
        return veri
    return eski


def ara(sorgu, k=None, vault=None, hook=False):
    """Return [(score, path, heading, snippet, matched_terms)] best first, one result per note."""
    vault = Path(vault) if vault else ortak.vault_kok()
    ay = ortak.ayarlar(vault)
    k = k or ay.get("recall_sonuc", 3)
    yuzey = [w for w in dict.fromkeys(re.split(r"[^a-z0-9]+", ortak.katla(sorgu))) if len(w) >= 2 and w not in DURAK]
    if not yuzey:
        return []
    syn = es_anlamlar()
    kaynak, agirlik = {}, {}          # term -> the query word it stands for, and its weight
    for w in yuzey:
        for f in kelimeler(w):
            kaynak.setdefault(f, w)
            agirlik[f] = 1.0
    for w in yuzey:
        # Turkish is agglutinative: "filmi", "kitaplarım", "bütçemi" are found through their longest known stem
        kok = next((w[:n] for n in range(len(w), 2, -1) if w[:n] in syn), None)
        for s in syn.get(kok, ()) if kok else ():
            for f in kelimeler(s) or [s]:
                if f not in agirlik:
                    kaynak[f], agirlik[f] = w, 0.6
    ix = indeks(vault)
    df, N, avgdl = ix["df"], max(1, ix["n"]), ix["avgdl"] or 1.0
    sonuclar = []
    for goreli, kayit in ix["dosyalar"].items():
        for p in kayit["p"]:
            tf = {}
            for w in p["t"]:
                if w in agirlik:
                    tf[w] = tf.get(w, 0) + 1
            if not tf:
                continue
            dl = len(p["t"]) or 1
            puan = 0.0
            for w, f in tf.items():
                idf = math.log(1 + (N - df.get(w, 0) + 0.5) / (df.get(w, 0) + 0.5))
                puan += agirlik[w] * idf * (f * 2.5) / (f + 1.5 * (0.25 + 0.75 * dl / avgdl))
            eslesen = {kaynak[w] for w in tf}
            sonuclar.append((puan, goreli, p["b"], p["m"], eslesen))
    sonuclar.sort(key=lambda s: -s[0])
    hafiza = ay["hafiza_klasoru"].rstrip("/") + "/"
    secilen, gorulen, hafiza_sayisi, ertelenen = [], set(), 0, []
    for s in sonuclar:
        if s[1] in gorulen:
            continue
        if s[1].startswith(hafiza) and hafiza_sayisi >= 1:
            ertelenen.append(s)        # the assistant's own memory may not crowd out the user's notes
            continue
        gorulen.add(s[1])
        hafiza_sayisi += s[1].startswith(hafiza)
        secilen.append(s)
        if len(secilen) == k:
            break
    for s in ertelenen:
        if len(secilen) >= k:
            break
        if s[1] not in gorulen:
            gorulen.add(s[1])
            secilen.append(s)
    if hook:
        # precision gate: a wrong pointer costs more attention than no pointer at all
        gerek = 1 if len(yuzey) <= 3 else 2
        secilen = [s for s in secilen if len(s[4]) >= gerek and s[0] >= ESIK]
    return secilen


def _ozet(metin, n=220):
    metin = " ".join(metin.split())
    return metin if len(metin) <= n else metin[: n - 1] + "…"


def isaretciler(istem):
    """Pointer block for a user prompt, or '' when nothing is relevant enough to be worth the attention."""
    if len(kelimeler(istem)) < 2 or istem.strip().startswith("/"):
        return ""
    try:
        bulunan = ara(istem, hook=True)
    except Exception as e:            # a broken search must never block the conversation
        print(f"Recall hatası: {e}", file=sys.stderr)
        return ""
    if not bulunan:
        return ""
    satirlar = ["[Recall] Vault'ta ilgili görünen yerler (otomatik arama; alıntı değil, işaretçi):"]
    for puan, goreli, baslik, metin, _ in bulunan:
        yer = goreli + (f" › {baslik}" if baslik else "")
        satirlar.append(f"• {yer} — \"{_ozet(metin)}\"")
    satirlar.append("Gerekirse dosyayı aç ve gerçek içeriğe bak; bu özetler kırpılmıştır.")
    return "\n".join(satirlar)


def hook():
    ortak.hook_baglami("UserPromptSubmit", isaretciler(ortak.hook_girdisi().get("prompt", "")))


def main(argv):
    if "--hook" in argv:
        hook()
        return 0
    if argv and argv[0] == "kur":
        ix = indeks(zorla=True)
        print(f"Recall indeksi kuruldu: {len(ix['dosyalar'])} not, {ix['n']} parça.")
        return 0
    sorgu = " ".join(argv[1:] if argv and argv[0] == "ara" else argv)
    if not sorgu.strip():
        print(__doc__)
        return 1
    bulunan = ara(sorgu, k=8)
    if not bulunan:
        print("Eşleşme yok.")
        return 0
    for puan, goreli, baslik, metin, _ in bulunan:
        print(f"[{puan:5.1f}] {goreli}" + (f" › {baslik}" if baslik else ""))
        print("        " + _ozet(metin, 260))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
