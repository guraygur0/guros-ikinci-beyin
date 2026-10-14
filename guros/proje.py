"""Project notes: one note per project, with its next step and what was learned along the way.

    python proje.py --yeni "Mobil Uygulama" --ne "Alışkanlık takip uygulaması" [--klasor C:/kod/app]
    python proje.py --adim "Mobil Uygulama" --satir "Giriş ekranını bitir"
    python proje.py --ogrendim "Mobil Uygulama" --satir "Expo'da ... şöyle çözülüyor"
    python proje.py --bitti "Mobil Uygulama" --satir "Giriş ekranını bitir"
    python proje.py --durum

Lessons are append-only: a line is added at the end of the "Öğrenilenler" section, nothing is rewritten.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

SABLON = """---
title: {ad}
type: proje
status: 🟢 aktif
klasor: {klasor}
basladi: {tarih}
tags: [proje]
---

# {ad}

**Ne:** {ne}

## Sıradaki adım

## Öğrenilenler

## İlgili Notlar
"""
GECERSIZ = re.compile(r'[<>:"/\\|?*]')


def _kok():
    ay = ortak.ayarlar()
    return ortak.vault_kok() / ay["proje_klasoru"]


def _not(ad):
    if GECERSIZ.search(ad):
        raise SystemExit(f'Proje adında şu karakterler olamaz: < > : " / \\ | ? * ({ad})')
    yol = _kok() / f"{ad}.md"
    if yol.exists():
        return yol
    for aday in _kok().glob("*.md"):                       # forgiving match: "mobil uygulama" finds "Mobil Uygulama.md"
        if ortak.katla(aday.stem) == ortak.katla(ad):
            return aday
    return yol


def yeni(ad, ne="", klasor=""):
    yol = _not(ad)
    if yol.exists():
        print(f"Zaten var: {yol.relative_to(ortak.vault_kok()).as_posix()}")
        return yol
    ortak.guvenli_yaz(yol, SABLON.format(ad=ad, ne=ne or "—", klasor=klasor or "", tarih=ortak.bugun()))
    print(f"Proje notu açıldı: {yol.relative_to(ortak.vault_kok()).as_posix()}")
    return yol


def _bolume_ekle(ad, bolum, satir):
    """Insert one line at the end of a section; the note is otherwise left byte-for-byte as it was."""
    yol = _not(ad)
    if not yol.exists():
        yeni(ad)
    eski = ortak.oku(yol)
    satirlar = eski.split("\n")
    bas = next((i for i, s in enumerate(satirlar) if re.match(rf"^##\s+{re.escape(bolum)}\s*$", s, re.I)), None)
    if bas is None:
        yeni_metin = eski.rstrip("\n") + f"\n\n## {bolum}\n\n{satir}\n"
    else:
        son = next((i for i in range(bas + 1, len(satirlar)) if re.match(r"^#{1,2}\s+", satirlar[i])), len(satirlar))
        ekle_yeri = son
        while ekle_yeri - 1 > bas and not satirlar[ekle_yeri - 1].strip():
            ekle_yeri -= 1
        if ekle_yeri == bas + 1:
            satirlar[ekle_yeri:ekle_yeri] = ["", satir]
        else:
            satirlar[ekle_yeri:ekle_yeri] = [satir]
        yeni_metin = "\n".join(satirlar)
    if not set(eski.split("\n")) <= set(yeni_metin.split("\n")):
        raise SystemExit("Güvenlik durdurması: ekleme sırasında var olan bir satır kaybolacaktı; dosyaya dokunulmadı.")
    ortak.guvenli_yaz(yol, yeni_metin)
    return yol


def ogrendim(ad, satir):
    yol = _bolume_ekle(ad, "Öğrenilenler", f"- [{ortak.bugun()}] {satir.strip()}")
    print(f"öğrenilenlere eklendi ({yol.stem}): {satir.strip()[:80]}")


def adim(ad, satir):
    yol = _bolume_ekle(ad, "Sıradaki adım", f"- [ ] {satir.strip()}")
    print(f"sıradaki adım eklendi ({yol.stem}): {satir.strip()[:80]}")


def bitti(ad, satir):
    yol = _not(ad)
    metin = ortak.oku(yol)
    hedef = f"- [ ] {satir.strip()}"
    if hedef not in metin:
        raise SystemExit(f"Açık adım bulunamadı: {satir.strip()}")
    ortak.guvenli_yaz(yol, metin.replace(hedef, f"- [x] {satir.strip()} ✅ {ortak.bugun()}", 1))
    print(f"tamamlandı ({yol.stem}): {satir.strip()[:80]}")


def durum():
    kok = _kok()
    notlar = sorted(p for p in kok.glob("*.md") if not p.name.startswith("_")) if kok.is_dir() else []
    if not notlar:
        print(f"Henüz proje yok. Açmak için: proje.py --yeni \"Ad\"  ({ortak.ayarlar()['proje_klasoru']}/ klasörüne yazar)")
        return
    for p in notlar:
        metin = ortak.oku(p)
        st = re.search(r"^status:\s*(.+)$", metin, re.M)
        acik = re.findall(r"^\s*-\s+\[ \]\s+(.+)$", metin, re.M)
        ogr = len(re.findall(r"^-\s+\[\d{4}-\d{2}-\d{2}\]", metin, re.M))
        print(f"• {p.stem}  [{st.group(1).strip() if st else '—'}]  {ogr} ders")
        if acik:
            print(f"    sıradaki: {acik[0].strip()}")


def main(argv):
    ap = argparse.ArgumentParser(description="GurOS proje notları")
    ap.add_argument("--yeni")
    ap.add_argument("--ne", default="")
    ap.add_argument("--klasor", default="")
    ap.add_argument("--ogrendim")
    ap.add_argument("--adim")
    ap.add_argument("--bitti")
    ap.add_argument("--satir", default="")
    ap.add_argument("--durum", action="store_true")
    a = ap.parse_args(argv)
    if a.yeni:
        yeni(a.yeni, a.ne, a.klasor)
    elif a.ogrendim or a.adim or a.bitti:
        if not a.satir.strip():
            ap.error("--satir gerekli")
        if a.ogrendim:
            ogrendim(a.ogrendim, a.satir)
        elif a.adim:
            adim(a.adim, a.satir)
        else:
            bitti(a.bitti, a.satir)
    else:
        durum()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
