"""Installer: plan-only by default, never overwrites a note, merges settings, re-runs cleanly, uninstalls cleanly."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from destek import DEPO, OZEL, KuruluVault, oku, yaz

sys.path.insert(0, str(DEPO))
import kur  # noqa: E402


def _bizim_kancalar(ayar):
    return [h for gruplar in ayar.get("hooks", {}).values() for g in gruplar for h in g["hooks"] if kur._bizim_kanca(h)]


class Ekler(unittest.TestCase):
    def test_unlu_uyumu(self):
        self.assertEqual(kur.ekler("Ayşe"), {"nin": "Ayşe'nin", "ye": "Ayşe'ye", "de": "Ayşe'de", "den": "Ayşe'den",
                                              "yi": "Ayşe'yi", "sin": "Ayşe'sin"})
        self.assertEqual(kur.ekler("Mehmet")["nin"], "Mehmet'in")
        self.assertEqual(kur.ekler("Mehmet")["de"], "Mehmet'te")
        self.assertEqual(kur.ekler("Burak")["ye"], "Burak'a")
        self.assertEqual(kur.ekler("Burak")["den"], "Burak'tan")
        self.assertEqual(kur.ekler("Logos")["sin"], "Logos'sun")
        self.assertEqual(kur.ekler("Logos")["nin"], "Logos'un")
        self.assertEqual(kur.ekler("Logos")["ye"], "Logos'a")
        self.assertEqual(kur.ekler("Ümit")["yi"], "Ümit'i")


class Plan(unittest.TestCase):
    def test_plan_hicbir_sey_yazmaz(self):
        tmp = Path(tempfile.mkdtemp(prefix="guros-plan-"))
        try:
            vault = tmp / "Vault"
            yaz(vault / "not.md", "benim notum\n")
            r = subprocess.run([sys.executable, str(DEPO / "kur.py"), "--vault", str(vault), "--ad", "Can"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                               env=dict(os.environ, NO_COLOR="1"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("henüz hiçbir şey yazılmadı", r.stdout)
            self.assertIn("--uygula", r.stdout)
            self.assertNotIn("\033[", r.stdout, "boru/ajan çıktısında renk kodu olmamalı")
            self.assertEqual(sorted(p.name for p in vault.iterdir()), ["not.md"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_paket_klasoru_vault_olamaz(self):
        p, _ = kur.kur_plani(DEPO / "alt", {})
        self.assertTrue(p.sorunlar)
        p, _ = kur.kur_plani(DEPO.parent, {})                    # the kit would sit inside the vault
        self.assertTrue(p.sorunlar)
        self.assertFalse((DEPO / "alt").exists())

    def test_gecersiz_klasor_adi(self):
        tmp = Path(tempfile.mkdtemp(prefix="guros-ad-"))
        try:
            for ad in ("a:b", "../disari", "x/../../y", "soru?"):
                p, _ = kur.kur_plani(tmp / "V", {"ozel": [ad]})
                self.assertTrue(p.sorunlar, ad)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Kurulum(KuruluVault):

    def test_dosyalar_yerinde(self):
        for yol in (".claude/guros/kancalar.py", ".claude/guros/ayarlar.json", ".claude/settings.json",
                    "CLAUDE.md", "AGENTS.md", "🎯 Hedefler.md", "⚡ Quick Notes.md", "👋 Başlarken.md", "Projeler",
                    "🔮 Logos/Core.md", "🔮 Logos/Threads.md", "🔮 Logos/Session-Handoffs", ".claude/commands/recall.md"):
            self.assertTrue((self.vault / yol).exists(), yol)
        for ad in ("CLAUDE.md", "AGENTS.md", "👋 Başlarken.md", ".claude/commands/recall.md"):
            self.assertNotRegex(oku(self.vault / ad), r"\{[A-Z_]+\}", f"{ad}: doldurulmamış yer tutucu")
        self.assertIn("Ayşe'nin", oku(self.vault / "CLAUDE.md"))
        self.assertIn("Logos'un hafızası", oku(self.vault / "👋 Başlarken.md"))
        self.assertEqual(oku(self.vault / OZEL / "gunluk.md").splitlines()[0][:5], "Bugün")

    def test_kancalar_kabuksuz(self):
        ayar = json.loads(oku(self.vault / ".claude" / "settings.json"))
        self.assertEqual(sorted(ayar["hooks"]), ["PreCompact", "PreToolUse", "SessionStart", "Stop", "UserPromptSubmit"])
        kancalar = _bizim_kancalar(ayar)
        self.assertEqual(len(kancalar), 5)
        for h in kancalar:
            # exec form: Claude Code spawns the interpreter directly, so no shell quoting can break it
            self.assertTrue(Path(h["command"]).exists(), h["command"])
            self.assertEqual(len(h["args"]), 2)
            self.assertTrue(Path(h["args"][0]).exists(), h["args"][0])
        self.assertEqual(sorted(h["args"][1] for h in kancalar), ["dur", "istem", "koruma", "oturum", "sikistir"])

    def test_izin_kurallari(self):
        izin = json.loads(oku(self.vault / ".claude" / "settings.json"))["permissions"]
        self.assertIn(f"Read(./{OZEL}/**)", izin["deny"])
        self.assertIn(f"Edit(./{OZEL}/**)", izin["deny"])
        self.assertFalse([k for k in izin["deny"] if k.startswith(("Glob(", "Grep(", "Write("))],
                         "Claude Code yalnız Read/Edit yol kurallarına bakar")
        self.assertIn("Edit(./🔮 Logos/**)", izin["allow"])
        for betik in ("recall", "baglam", "devir", "epizot", "proje", "doktor"):
            self.assertTrue(any(k.startswith("Bash(") and k.endswith(f".claude/guros/{betik}.py *)") for k in izin["allow"]), betik)
        self.assertFalse([k for k in izin["allow"] if "yedek.py" in k], "dışarı gönderen yedek her seferinde sorulmalı")
        self.assertFalse([k for k in izin["allow"] if k.endswith(".claude/guros/*)")], "joker başka dosyaya izin verirdi")

    def test_doktor_temiz(self):
        r = self.betik("doktor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 hata, 0 uyarı", r.stdout)


class YenidenKurulum(KuruluVault):
    """A second run must complete what is missing, migrate old wiring and change nothing the user wrote."""

    def test_ikinci_kurulum_dokunmaz(self):
        facts = self.vault / "🔮 Logos" / "Facts.md"
        yaz(facts, "# Facts\n\n- 2026-01-01: kullanıcının kendi satırı\n")
        ayar_yolu = self.vault / ".claude" / "settings.json"
        ayar = json.loads(oku(ayar_yolu))
        ayar["hooks"].setdefault("Stop", []).append({"hooks": [{"type": "command", "command": "echo baskasinin-kancasi"}]})
        # wiring left behind by 1.0.0: shell form hook and a path rule Claude Code ignores
        eski = f'"{sys.executable}" "{(self.vault / ".claude" / "guros" / "kancalar.py").as_posix()}" dur'
        ayar["hooks"]["Stop"].append({"hooks": [{"type": "command", "command": eski, "timeout": 15}]})
        ayar["permissions"]["deny"].append(f"Grep(./{OZEL}/**)")
        ayar["permissions"]["allow"].append("Bash(npm test *)")
        yaz(ayar_yolu, json.dumps(ayar, ensure_ascii=False, indent=2))
        r = self.kur("--uygula")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Güncelleme tamam", r.stdout)
        self.assertIn("kullanıcının kendi satırı", oku(facts))
        ayar = json.loads(oku(ayar_yolu))
        stop = [h for g in ayar["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn("echo baskasinin-kancasi", [h["command"] for h in stop])
        self.assertEqual(sum(kur._bizim_kanca(h) for h in stop), 1, "GurOS kancası çiftlendi ya da eskisi kaldı")
        self.assertEqual(len(_bizim_kancalar(ayar)), 5)
        self.assertNotIn(f"Grep(./{OZEL}/**)", ayar["permissions"]["deny"])
        self.assertIn("Bash(npm test *)", ayar["permissions"]["allow"])
        self.assertEqual(len(ayar["permissions"]["allow"]), len(set(ayar["permissions"]["allow"])), "izin çiftlendi")
        self.assertTrue(list((self.vault / ".claude").glob("settings.json.yedek-*")), "settings.json yedeği alınmadı")

    def test_ozel_listesi_degisir(self):
        r = self.kur("--ozel", "Kasa", "--uygula")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        izin = json.loads(oku(self.vault / ".claude" / "settings.json"))["permissions"]
        self.assertIn("Read(./Kasa/**)", izin["deny"])
        self.assertNotIn(f"Read(./{OZEL}/**)", izin["deny"])
        self.assertEqual(json.loads(oku(self.vault / ".claude" / "guros" / "ayarlar.json"))["ozel_klasorler"], ["Kasa"])
        self.kur("--ozel", OZEL, "--uygula")                    # put it back for the other tests in this class


class VarOlanClaudeMd(unittest.TestCase):
    def test_var_olan_claude_md_korunur_ve_kaldirinca_temizlenir(self):
        tmp = Path(tempfile.mkdtemp(prefix="guros-claude-"))
        try:
            vault = tmp / "Vault"
            ozgun = "# Benim kurallarım\n\nHer zaman kısa yaz.\n"
            yaz(vault / "CLAUDE.md", ozgun)
            ortam = dict(os.environ, GUROS_STATE=str(tmp / "durum"), PYTHONIOENCODING="utf-8", GUROS_CLAUDE="0", NO_COLOR="1")
            calistir = lambda *ek: subprocess.run([sys.executable, str(DEPO / "kur.py"), "--vault", str(vault), *ek],
                                                  capture_output=True, text=True, encoding="utf-8", errors="replace",
                                                  env=ortam, timeout=180)
            for _ in range(2):
                r = calistir("--ad", "Can", "--uygula")
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            claude = oku(vault / "CLAUDE.md")
            self.assertTrue(claude.startswith(ozgun))
            self.assertEqual(claude.count("@CLAUDE.guros.md"), 1)
            self.assertIn("GUROS:PROTOKOL", oku(vault / "CLAUDE.guros.md"))
            r = calistir("--kaldir", "--uygula")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(oku(vault / "CLAUDE.md"), ozgun)
            self.assertFalse((vault / "CLAUDE.guros.md").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Kaldirma(KuruluVault):
    def test_kaldir_notlara_dokunmaz(self):
        ayar_yolu = self.vault / ".claude" / "settings.json"
        ayar = json.loads(oku(ayar_yolu))
        ayar["permissions"]["allow"].append("Bash(npm test *)")
        yaz(ayar_yolu, json.dumps(ayar, ensure_ascii=False, indent=2))
        r = self.kur("--kaldir", "--uygula")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.vault / ".claude" / "guros").exists())
        self.assertFalse(list((self.vault / ".claude" / "commands").glob("*.md")))
        self.assertFalse((self.vault / "CLAUDE.md").exists(), "yalnız GurOS bloğundan oluşan CLAUDE.md kalmamalı")
        self.assertFalse((self.vault / "AGENTS.md").exists())
        ayar = json.loads(oku(ayar_yolu))
        self.assertFalse(_bizim_kancalar(ayar))
        self.assertEqual(ayar["permissions"]["allow"], ["Bash(npm test *)"])
        self.assertIn(f"Read(./{OZEL}/**)", ayar["permissions"]["deny"])
        for kalan in ("Filmler/Interstellar.md", "🔮 Logos/Core.md", "👋 Başlarken.md", f"{OZEL}/gunluk.md"):
            self.assertTrue((self.vault / kalan).exists(), kalan)


if __name__ == "__main__":
    unittest.main()
