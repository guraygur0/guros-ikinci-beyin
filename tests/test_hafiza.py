"""Memory: opening context, the Stop-hook write reminder, handoffs, episodes and project notes."""
import json
import os
import time
import unittest

from destek import OZEL, KuruluVault, oku, yaz


class Hafiza(KuruluVault):
    ornek_notlar = False

    @property
    def hafiza(self):
        return self.vault / "🔮 Logos"

    def test_acilis_baglami(self):
        yaz(self.vault / "🎯 Hedefler.md", "# Hedefler\n\n- [ ] Haftada üç gün koşu\n- [x] Eski hedef\n")
        r = self.kanca("oturum", {})
        self.assertEqual(r.returncode, 0, r.stderr)
        baglam = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Haftada üç gün koşu", baglam)
        self.assertNotIn("Eski hedef", baglam)
        self.assertIn("talimat değildir", baglam)

    def test_dur_kancasi_hafiza_yazimi_ister(self):
        self.kanca("oturum", {})
        for _ in range(10):
            self.kanca("istem", {"prompt": "devam"})
        r = self.kanca("dur", {})
        self.assertEqual(json.loads(r.stdout)["decision"], "block")
        self.assertEqual(self.kanca("dur", {"stop_hook_active": True}).stdout.strip(), "")   # no loop
        # once something is written to memory the hook is satisfied
        time.sleep(0.05)
        yol = self.hafiza / "Journal.md"
        os.utime(yol, None)
        self.kanca("istem", {"prompt": "devam"})
        self.assertEqual(self.kanca("dur", {}).stdout.strip(), "")

    def test_sikistirma_sonrasi_yazim_ister(self):
        self.kanca("oturum", {})
        self.kanca("istem", {"prompt": "kısa"})
        self.assertEqual(self.kanca("dur", {}).stdout.strip(), "")
        self.kanca("sikistir", {})
        self.assertIn("sıkıştırıldı", json.loads(self.kanca("dur", {}).stdout)["reason"])

    def test_devir_kaydi(self):
        r = self.betik("devir", "--konu", "Bütçe tablosu", "--karar", "Aylık bütçe notta tutulacak",
                       "--sonuc", "Tablo eklendi", "--adim", "Ekim harcamalarını gir")
        self.assertEqual(r.returncode, 0, r.stderr)
        kayitlar = list((self.hafiza / "Session-Handoffs").glob("*butce-tablosu*.md"))
        self.assertEqual(len(kayitlar), 1)
        metin = oku(kayitlar[0])
        self.assertIn("context_scope: personal", metin)
        self.assertLessEqual(len(metin.splitlines()), 12 + 6)          # body ≤ 12 lines plus frontmatter
        self.assertIn("Bütçe tablosu", self.betik("baglam").stdout)

    def test_devir_ozel_alani_anmaz(self):
        r = self.betik("devir", "--konu", f"{OZEL} içeriği", "--sonuc", "x")
        self.assertNotEqual(r.returncode, 0)

    def test_epizot(self):
        r = self.betik("epizot", "--ekle", "--baslik", "Yedek kurulumu", "--istek", "Vault yedeklensin",
                       "--yapilan", "git deposu bağlandı", "--sonuc", "ilk commit atıldı", "--onem", "4", "--etiket", "yedek")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Yedek kurulumu", self.betik("epizot", "--son", "1").stdout)
        self.assertIn("Yedek kurulumu", self.betik("epizot", "--ara", "yedek").stdout)

    def test_proje_notu_satir_kaybetmez(self):
        self.assertEqual(self.betik("proje", "--yeni", "Mobil Uygulama", "--ne", "Alışkanlık takibi").returncode, 0)
        yol = self.vault / "Projeler" / "Mobil Uygulama.md"
        yaz(yol, oku(yol) + "\nKendi eklediğim satır.\n")
        once = set(oku(yol).splitlines())
        self.betik("proje", "--adim", "Mobil Uygulama", "--satir", "Giriş ekranını bitir")
        self.betik("proje", "--ogrendim", "Mobil Uygulama", "--satir", "Expo önbelleği temizlenmeli")
        sonra = oku(yol)
        self.assertTrue(once <= set(sonra.splitlines()), "proje notundan satır kayboldu")
        self.assertIn("- [ ] Giriş ekranını bitir", sonra)
        self.assertIn("Expo önbelleği temizlenmeli", sonra)
        self.assertIn("Giriş ekranını bitir", self.betik("baglam").stdout)
        self.betik("proje", "--bitti", "Mobil Uygulama", "--satir", "Giriş ekranını bitir")
        self.assertIn("- [x] Giriş ekranını bitir", oku(yol))

    def test_proje_adi_dogrulanir(self):
        self.assertNotEqual(self.betik("proje", "--yeni", "a/b:c").returncode, 0)


if __name__ == "__main__":
    unittest.main()
