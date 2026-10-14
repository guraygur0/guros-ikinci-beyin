"""Installer: plan-only by default, never overwrites a note, merges settings, re-runs cleanly, uninstalls cleanly."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from destek import DEPO, OZEL, KuruluVault, oku, yaz

sys.path.insert(0, str(DEPO))
import kur  # noqa: E402


class Ekler(unittest.TestCase):
    def test_unlu_uyumu(self):
        self.assertEqual(kur.ekler("Ayşe"), {"nin": "Ayşe'nin", "ye": "Ayşe'ye", "de": "Ayşe'de", "den": "Ayşe'den",
                                              "yi": "Ayşe'yi", "sin": "Ayşe'sin"})
        self.assertEqual(kur.ekler("Mehmet")["nin"], "Mehmet'in")
        self.assertEqual(kur.ekler("Mehmet")["de"], "Mehmet'te")
        self.assertEqual(kur.ekler("Burak")["ye"], "Burak'a")
        self.assertEqual(kur.ekler("Burak")["den"], "Burak'tan")
        self.assertEqual(kur.ekler("Logos")["sin"], "Logos'sun")
        self.assertEqual(kur.ekler("Ümit")["yi"], "Ümit'i")


class Plan(unittest.TestCase):
    def test_plan_hicbir_sey_yazmaz(self):
        tmp = Path(tempfile.mkdtemp(prefix="guros-plan-"))
        try:
            vault = tmp / "Vault"
            yaz(vault / "not.md", "benim notum\n")
            r = subprocess.run([sys.executable, str(DEPO / "kur.py"), "--vault", str(vault), "--ad", "Can"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("[PLAN]", r.stdout)
            self.assertEqual(sorted(p.name for p in vault.iterdir()), ["not.md"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Kurulum(KuruluVault):

    def test_dosyalar_yerinde(self):
        for yol in (".claude/guros/kancalar.py", ".claude/guros/ayarlar.json", ".claude/settings.json",
                    "CLAUDE.md", "AGENTS.md", "🎯 Hedefler.md", "⚡ Quick Notes.md", "Projeler",
                    "🔮 Logos/Core.md", "🔮 Logos/Threads.md", "🔮 Logos/Session-Handoffs", ".claude/commands/recall.md"):
            self.assertTrue((self.vault / yol).exists(), yol)
        claude = oku(self.vault / "CLAUDE.md")
        self.assertIn("Ayşe'nin", claude)
        self.assertNotRegex(claude, r"\{[A-Z_]+\}", "doldurulmamış yer tutucu")
        self.assertEqual(oku(self.vault / OZEL / "gunluk.md").splitlines()[0][:5], "Bugün")

    def test_ayarlar_birlesir(self):
        ayar = json.loads(oku(self.vault / ".claude" / "settings.json"))
        self.assertEqual(sorted(ayar["hooks"]), ["PreCompact", "PreToolUse", "SessionStart", "Stop", "UserPromptSubmit"])
        self.assertIn(f"Read(./{OZEL}/**)", ayar["permissions"]["deny"])
        self.assertIn(f"Edit(./{OZEL}/**)", ayar["permissions"]["deny"])
        self.assertFalse([k for k in ayar["permissions"]["deny"] if k.startswith(("Glob(", "Grep(", "Write("))],
                         "Claude Code yalnız Read/Edit yol kurallarına bakar")

    def test_doktor_temiz(self):
        r = self.betik("doktor")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 hata", r.stdout)


class YenidenKurulum(KuruluVault):
    """A second run must complete what is missing and change nothing the user wrote."""

    def test_ikinci_kurulum_dokunmaz(self):
        facts = self.vault / "🔮 Logos" / "Facts.md"
        yaz(facts, "# Facts\n\n- 2026-01-01: kullanıcının kendi satırı\n")
        ayar_yolu = self.vault / ".claude" / "settings.json"
        ayar = json.loads(oku(ayar_yolu))
        ayar["hooks"].setdefault("Stop", []).append({"hooks": [{"type": "command", "command": "echo baskasinin-kancasi"}]})
        ayar["permissions"]["deny"].append(f"Grep(./{OZEL}/**)")               # left behind by an older version
        yaz(ayar_yolu, json.dumps(ayar, ensure_ascii=False, indent=2))
        r = self.kur("--uygula")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("kullanıcının kendi satırı", oku(facts))
        ayar = json.loads(oku(ayar_yolu))
        komutlar = [h["command"] for g in ayar["hooks"]["Stop"] for h in g["hooks"]]
        self.assertIn("echo baskasinin-kancasi", komutlar)
        self.assertEqual(sum("kancalar.py" in k for k in komutlar), 1, "GurOS kancası çiftlendi")
        self.assertNotIn(f"Grep(./{OZEL}/**)", ayar["permissions"]["deny"])
        self.assertTrue(list((self.vault / ".claude").glob("settings.json.yedek-*")), "settings.json yedeği alınmadı")


class VarOlanClaudeMd(unittest.TestCase):
    def test_var_olan_claude_md_korunur(self):
        tmp = Path(tempfile.mkdtemp(prefix="guros-claude-"))
        try:
            vault = tmp / "Vault"
            yaz(vault / "CLAUDE.md", "# Benim kurallarım\n\nHer zaman kısa yaz.\n")
            ortam = {**__import__("os").environ, "GUROS_STATE": str(tmp / "durum"), "PYTHONIOENCODING": "utf-8"}
            for _ in range(2):
                r = subprocess.run([sys.executable, str(DEPO / "kur.py"), "--vault", str(vault), "--ad", "Can", "--uygula"],
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", env=ortam, timeout=180)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            claude = oku(vault / "CLAUDE.md")
            self.assertTrue(claude.startswith("# Benim kurallarım\n\nHer zaman kısa yaz.\n"))
            self.assertEqual(claude.count("@CLAUDE.guros.md"), 1)
            self.assertIn("GUROS:PROTOKOL", oku(vault / "CLAUDE.guros.md"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Kaldirma(KuruluVault):
    def test_kaldir_notlara_dokunmaz(self):
        r = self.kur("--kaldir", "--uygula")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse((self.vault / ".claude" / "guros").exists())
        ayar = json.loads(oku(self.vault / ".claude" / "settings.json"))
        self.assertFalse(any("kancalar.py" in h["command"] for g in sum(ayar.get("hooks", {}).values(), []) for h in g["hooks"]))
        self.assertIn(f"Read(./{OZEL}/**)", ayar["permissions"]["deny"])
        self.assertTrue((self.vault / "Filmler" / "Interstellar.md").exists())
        self.assertTrue((self.vault / "🔮 Logos" / "Core.md").exists())


if __name__ == "__main__":
    unittest.main()
