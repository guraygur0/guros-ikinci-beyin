"""Daily maintenance: refresh the search index, run the health check, back up if a backup is configured.

    python bakim.py

Meant for a scheduler (Windows Task Scheduler, cron, launchd); see docs/BAKIM.md. Safe to run any time.
Writes a one-line result to the machine-local state folder; nothing in the vault changes except the backup commit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402


def main():
    import doktor
    import recall
    import yedek
    durum = []
    try:
        ix = recall.indeks(zorla=True)
        durum.append(f"indeks {len(ix['dosyalar'])} not")
    except Exception as e:
        durum.append(f"indeks HATA {e}")
    kod = doktor.kontrol(sessiz=True)
    durum.append("doktor temiz" if kod == 0 else "doktor HATA")
    try:
        y = yedek.yedekle(sessiz=True)
        durum.append({0: "yedek tamam", 1: "yedek gönderilemedi", 2: "yedek DURDU"}.get(y, f"yedek {y}"))
    except Exception as e:
        durum.append(f"yedek HATA {e}")
    satir = f"{ortak.simdi()}  " + " · ".join(durum)
    ortak.ekle(ortak.durum_dizini() / "bakim.log", satir)
    print(satir)
    return 0 if kod == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
