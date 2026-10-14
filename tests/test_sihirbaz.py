"""Wizard and discovery: finds Obsidian vaults, suggests private folders by name only, installs, updates, removes, cancels."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from destek import DEPO, oku, yaz

sys.path.insert(0, str(DEPO))
import kur  # noqa: E402


class Kesif(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guros-kesif-")).resolve()
        self.eski = os.environ.get("GUROS_OBSIDIAN_JSON")

    def tearDown(self):
        if self.eski is None:
            os.environ.pop("GUROS_OBSIDIAN_JSON", None)
        else:
            os.environ["GUROS_OBSIDIAN_JSON"] = self.eski
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_obsidian_vaultlari(self):
        for ad in ("Okul", "Notlarım"):
            (self.tmp / ad).mkdir()
        yaz(self.tmp / "obsidian.json", json.dumps({"vaults": {
            "a": {"path": str(self.tmp / "Okul"), "ts": 100},
            "b": {"path": str(self.tmp / "Notlarım"), "ts": 300, "open": True},
            "c": {"path": str(self.tmp / "silinmis"), "ts": 500},
            "d": {"path": "", "ts": 900}}}))
        os.environ["GUROS_OBSIDIAN_JSON"] = str(self.tmp / "obsidian.json")
        self.assertEqual(kur.obsidian_vaultlari(), [("Notlarım", self.tmp / "Notlarım"), ("Okul", self.tmp / "Okul")])

    def test_bozuk_ya_da_olmayan_obsidian_json(self):
        os.environ["GUROS_OBSIDIAN_JSON"] = str(self.tmp / "yok.json")
        self.assertEqual(kur.obsidian_vaultlari(), [])
        yaz(self.tmp / "bozuk.json", "{bozuk")
        os.environ["GUROS_OBSIDIAN_JSON"] = str(self.tmp / "bozuk.json")
        self.assertEqual(kur.obsidian_vaultlari(), [])

    def test_ozel_adaylar_yalniz_adlara_bakar(self):
        for d in ("Günlük", "✍️ Journaling", "Özellikler", "Projeler", "Hayat/Kişisel", "Hayat/Spor", "🔮 Logos/özel-notlar",
                  ".gizli-sistem", "Arşiv/Diary 2024"):
            (self.tmp / d).mkdir(parents=True)
        self.assertEqual(kur.ozel_adaylar(self.tmp, haric={"🔮 Logos"}),
                         ["Arşiv/Diary 2024", "Günlük", "Hayat/Kişisel", "✍️ Journaling"])


class Sihirbaz(unittest.TestCase):
    """The wizard is driven through stdin, exactly as a person would type."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="guros-sihirbaz-")).resolve()
        self.vault = self.tmp / "Notlarım"
        (self.vault / ".obsidian").mkdir(parents=True)
        (self.vault / "Günlük").mkdir()
        yaz(self.vault / "Günlük" / "bugun.md", "kimse okumasın\n")
        yaz(self.vault / "Fikirler.md", "benim notum\n")
        yaz(self.tmp / "obsidian.json", json.dumps({"vaults": {"a": {"path": str(self.vault), "ts": 1}}}))
        self.ortam = dict(os.environ, GUROS_SIHIRBAZ="1", GUROS_CLAUDE="0", NO_COLOR="1", PYTHONIOENCODING="utf-8",
                          GUROS_STATE=str(self.tmp / "durum"), GUROS_OBSIDIAN_JSON=str(self.tmp / "obsidian.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sihirbaz(self, cevaplar):
        return subprocess.run([sys.executable, str(DEPO / "kur.py")], input="\n".join(cevaplar) + "\n",
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=self.ortam, timeout=240)

    def ayarlar(self):
        return json.loads(oku(self.vault / ".claude" / "guros" / "ayarlar.json"))

    def test_kur_guncelle_kaldir(self):
        # 1st vault · name · default assistant · close the suggested folder · default private folder · no extra · install
        r = self.sihirbaz(["1", "Deniz", "", "e", "", "", "e"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Notlarım", r.stdout)
        self.assertIn("Günlük", r.stdout)
        self.assertIn("Kurulum tamam", r.stdout)
        self.assertIn("irm https://claude.ai/install.ps1" if os.name == "nt" else "curl -fsSL https://claude.ai/install.sh", r.stdout)
        ay = self.ayarlar()
        self.assertEqual((ay["ad"], ay["asistan"]), ("Deniz", "Logos"))
        self.assertEqual(ay["ozel_klasorler"], ["🔒 Özel Alan", "Günlük"])
        self.assertEqual(oku(self.vault / "Fikirler.md"), "benim notum\n")
        self.assertEqual(oku(self.vault / "Günlük" / "bugun.md"), "kimse okumasın\n")

        r = self.sihirbaz(["1", "1", "e"])                       # same vault again → update
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("zaten kurulu", r.stdout)
        self.assertIn("Güncelleme tamam", r.stdout)
        self.assertEqual(self.ayarlar()["ozel_klasorler"], ["🔒 Özel Alan", "Günlük"])

        r = self.sihirbaz(["1", "2", "e"])                       # → remove
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("kaldırıldı", r.stdout)
        self.assertFalse((self.vault / ".claude" / "guros").exists())
        self.assertTrue((self.vault / "🔮 Logos" / "Core.md").exists())

    def test_reddedince_hicbir_sey_yazilmaz(self):
        r = self.sihirbaz(["1", "Deniz", "Ada", "h", "", "", "h"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("hiçbir şey yazılmadı", r.stdout)
        self.assertEqual(sorted(p.name for p in self.vault.iterdir()), [".obsidian", "Fikirler.md", "Günlük"])

    def test_yarida_birakilinca_hicbir_sey_yazilmaz(self):
        r = self.sihirbaz(["1"])                                 # input ends before the name
        self.assertEqual(r.returncode, 130, r.stdout + r.stderr)
        self.assertIn("İptal", r.stdout)
        self.assertFalse((self.vault / ".claude").exists())

    def test_yeni_klasor_yolu(self):
        yeni = self.tmp / "Yepyeni Vault"
        r = self.sihirbaz([str(yeni), "Deniz", "", "Kasa", "", "e"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((yeni / "Kasa" / "Burası özel.md").exists())
        self.assertEqual(json.loads(oku(yeni / ".claude" / "guros" / "ayarlar.json"))["ozel_klasorler"], ["Kasa"])

    def test_vaultlar_listesi(self):
        r = subprocess.run([sys.executable, str(DEPO / "kur.py"), "--vaultlar"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=self.ortam, timeout=60)
        self.assertEqual(r.stdout.strip(), f"Notlarım\t{self.vault}")

    def test_terminal_degilse_soru_sormaz(self):
        ortam = dict(self.ortam)
        ortam.pop("GUROS_SIHIRBAZ")
        r = subprocess.run([sys.executable, str(DEPO / "kur.py")], input="", capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=ortam, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn("--vault gerekli", r.stderr)


if __name__ == "__main__":
    unittest.main()
