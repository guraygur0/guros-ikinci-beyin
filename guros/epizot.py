"""Episodic memory: what was asked, what was done, how it ended — one dated entry per piece of work.

    python epizot.py --ekle --baslik "..." --istek "..." --yapilan "..." --sonuc "..." [--onem 1-5] [--etiket a,b]
    python epizot.py --ara "yedek kurulumu" [-k 3]
    python epizot.py --son 3

Entries live in a plain Markdown file inside the memory folder, newest first, so Recall indexes them for free.
Ranking = recency + importance + relevance (the trio from the "Generative Agents" paper).
"""
import argparse
import datetime as dt
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402
import recall  # noqa: E402

DOSYA = "📼 Epizotlar.md"
ARSIV = "📼 Epizotlar Arşiv.md"
TAVAN = 60
BASLIK = "# 📼 Epizotlar\n\nHer kayıt bir iş: ne istendi, ne yapıldı, nasıl bitti. En yeni üstte. `epizot.py` yazar.\n"
KAYIT = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (.+?)\n(.*?)(?=^### |\Z)", re.M | re.S)


def _yol(ad):
    return ortak.hafiza_dizini() / ad


def _kayitlar(metin):
    out = []
    for m in KAYIT.finditer(metin):
        govde = m.group(3)
        onem = re.search(r"\*\*Önem:\*\*\s*(\d)", govde)
        out.append({"zaman": m.group(1), "baslik": m.group(2).strip(), "govde": govde.strip(),
                    "onem": int(onem.group(1)) if onem else 3, "ham": m.group(0)})
    return out


def ekle(baslik, istek, yapilan, sonuc, onem=3, etiket=""):
    klasor = ortak.ozel_anilir(" ".join([baslik, istek, yapilan, sonuc, etiket]))
    if klasor:
        raise SystemExit(f"Epizot yazılmadı: metinde özel klasörün adı geçiyor ({klasor}).")
    onem = max(1, min(5, int(onem)))
    kayit = (f"### {ortak.simdi()} · {baslik.strip()}\n"
             f"- **İstek:** {istek.strip()}\n- **Yapılan:** {yapilan.strip()}\n- **Sonuç:** {sonuc.strip()}\n"
             f"- **Önem:** {onem}" + (f" · **Etiket:** {etiket.strip()}" if etiket.strip() else "") + "\n\n")
    yol = _yol(DOSYA)
    metin = ortak.oku(yol) or BASLIK
    kayitlar = _kayitlar(metin)
    bas = metin.split("### ", 1)[0] if kayitlar else metin
    if not bas.endswith("\n\n"):
        bas = bas.rstrip("\n") + "\n\n"
    tut = kayitlar[: TAVAN - 1]
    tasan = kayitlar[TAVAN - 1:]
    if tasan:
        arsiv = _yol(ARSIV)
        if not ortak.oku(arsiv):
            ortak.guvenli_yaz(arsiv, "# 📼 Epizotlar Arşiv\n\nAna dosyadan taşan eski kayıtlar. Silinmez, yalnızca kenara alınır.\n\n")
        for k in tasan:
            ortak.ekle(arsiv, k["ham"].rstrip() + "\n")
    ortak.guvenli_yaz(yol, bas + kayit + "".join(k["ham"].rstrip() + "\n\n" for k in tut))
    print(f"epizot yazıldı: {ortak.simdi()} · {baslik.strip()}" + (f" ({len(tasan)} kayıt arşive indi)" if tasan else ""))


def _puan(kayit, sorgu_kelimeleri, simdi):
    try:
        gun = (simdi - dt.datetime.strptime(kayit["zaman"], "%Y-%m-%d %H:%M")).total_seconds() / 86400
    except ValueError:
        gun = 365
    tazelik = math.exp(-max(0.0, gun) / 30)
    onem = kayit["onem"] / 5
    if not sorgu_kelimeleri:
        return tazelik + onem
    kendi = set(recall.kelimeler(kayit["baslik"] + " " + kayit["govde"]))
    ilgi = len(kendi & sorgu_kelimeleri) / len(sorgu_kelimeleri)
    return (0.5 * tazelik + 0.5 * onem + 2.0 * ilgi) if ilgi else 0.0


def bul(sorgu="", k=3):
    kayitlar = _kayitlar(ortak.oku(_yol(DOSYA))) + _kayitlar(ortak.oku(_yol(ARSIV)))
    kelime = set(recall.kelimeler(sorgu))
    simdi = dt.datetime.now()
    puanli = sorted(((_puan(r, kelime, simdi), r) for r in kayitlar), key=lambda x: -x[0])
    return [(p, r) for p, r in puanli if p > 0][:k]


def main(argv):
    ap = argparse.ArgumentParser(description="GurOS epizot kaydı")
    ap.add_argument("--ekle", action="store_true")
    ap.add_argument("--baslik", default="")
    ap.add_argument("--istek", default="")
    ap.add_argument("--yapilan", default="")
    ap.add_argument("--sonuc", default="")
    ap.add_argument("--onem", type=int, default=3)
    ap.add_argument("--etiket", default="")
    ap.add_argument("--ara", default=None)
    ap.add_argument("--son", type=int, default=None)
    ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args(argv)
    if a.ekle:
        if not (a.baslik and a.istek and a.yapilan and a.sonuc):
            ap.error("--ekle için --baslik, --istek, --yapilan ve --sonuc gerekli")
        ekle(a.baslik, a.istek, a.yapilan, a.sonuc, a.onem, a.etiket)
        return 0
    sonuc = bul(a.ara or "", a.son or a.k)
    if not sonuc:
        print("Epizot bulunamadı.")
    for p, r in sonuc:
        print(f"• {r['zaman']} · {r['baslik']} ({p:.2f})")
        for satir in r["govde"].splitlines()[:3]:
            print("    " + satir.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
