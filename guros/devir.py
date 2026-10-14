"""Session handoff: a short note that lets the next conversation pick up where this one stopped.

    python devir.py --konu "Bütçe tablosu" --karar "Aylık bütçe Excel yerine notta tutulacak" \
                    --sonuc "Finans notuna tablo eklendi" --adim "Ekim harcamalarını gir" [--kapsam personal|system]

At most 12 lines. 'personal' records (goals, projects, the user's decisions) appear in the next opening context;
'system' records (setup, tests) stay searchable but out of the way.
"""
import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

SINIR = 12


def _slug(metin):
    s = re.sub(r"[^a-z0-9]+", "-", ortak.katla(metin)).strip("-")
    return s[:40] or "oturum"


def yaz(konu, kararlar=(), sonuclar=(), adimlar=(), kapsam="personal", kaynak=""):
    if kapsam not in ("personal", "system"):
        raise SystemExit("--kapsam personal ya da system olmalı")
    klasor = ortak.ozel_anilir(" ".join([konu, *kararlar, *sonuclar, *adimlar, kaynak]))
    if klasor:
        raise SystemExit(f"Devir kaydı yazılmadı: metinde özel klasörün adı geçiyor ({klasor}).")
    govde = [f"- Tarih: {ortak.bugun()} · Konu: {konu.strip()}"]
    govde += [f"- [decision] {k.strip()}" for k in kararlar if k.strip()]
    govde += [f"- [result] {s.strip()}" for s in sonuclar if s.strip()]
    govde += [f"- [next_step] {a.strip()}" for a in adimlar if a.strip()]
    if kaynak.strip():
        govde.append(f"- Kaynak: {kaynak.strip()}")
    satirlar = ["---", f"context_scope: {kapsam}", "---", *govde]
    if len(satirlar) > SINIR:
        raise SystemExit(f"Devir kaydı en fazla {SINIR} satır olmalı ({len(satirlar)} satır geldi). Kısalt.")
    kok = ortak.hafiza_dizini() / "Session-Handoffs"
    ad = f"{ortak.bugun()}-{_slug(konu)}"
    yol = kok / f"{ad}.md"
    if yol.exists():                                    # never overwrite another conversation's record
        yol = kok / f"{ad}-{int(time.time()) % 100000}.md"
    ortak.guvenli_yaz(yol, "\n".join(satirlar) + "\n")
    print(f"devir kaydı yazıldı: {yol.relative_to(ortak.vault_kok()).as_posix()}")
    return yol


def main(argv):
    ap = argparse.ArgumentParser(description="GurOS devir kaydı")
    ap.add_argument("--konu", required=True)
    ap.add_argument("--karar", action="append", default=[])
    ap.add_argument("--sonuc", action="append", default=[])
    ap.add_argument("--adim", action="append", default=[])
    ap.add_argument("--kapsam", default="personal")
    ap.add_argument("--kaynak", default="")
    a = ap.parse_args(argv)
    yaz(a.konu, a.karar, a.sonuc, a.adim, a.kapsam, a.kaynak)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
