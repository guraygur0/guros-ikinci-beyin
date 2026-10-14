"""Shared test scaffolding: a throw-away vault installed with kur.py, and helpers to run its scripts and hooks.

Every test works in a fresh temporary folder with its own GUROS_STATE, so nothing touches a real vault
or the real ~/.guros state folder.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DEPO = Path(__file__).resolve().parents[1]
OZEL = "🔒 Özel Alan"


def yaz(yol, metin):
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    with io.open(yol, "w", encoding="utf-8", newline="\n") as f:
        f.write(metin)


def oku(yol):
    with io.open(yol, encoding="utf-8") as f:
        return f.read()


class KuruluVault(unittest.TestCase):
    """One installed vault per test class (installing takes a couple of seconds)."""

    ad = "Ayşe"
    ornek_notlar = True

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="guros-test-"))
        cls.vault = (cls.tmp / "Deneme Vault").resolve()
        cls.durum = cls.tmp / "durum"
        cls.ortam = dict(os.environ, GUROS_VAULT=str(cls.vault), GUROS_STATE=str(cls.durum), PYTHONIOENCODING="utf-8")
        if cls.ornek_notlar:
            yaz(cls.vault / "Filmler" / "Interstellar.md",
                "# Interstellar\n\nUzay, kara delik ve zaman üzerine bir bilim kurgu. Christopher Nolan.\n")
            yaz(cls.vault / "Finans" / "Bütçe.md", "# Bütçe\n\nAylık harcama tablosu ve birikim hedefi.\n")
            yaz(cls.vault / OZEL / "gunluk.md", "Bugün çok yorgundum, kimseye söylemedim. zirzop\n")
        r = cls.kur("--uygula")
        if r.returncode != 0:
            raise AssertionError("kurulum başarısız:\n" + r.stdout + r.stderr)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def kur(cls, *ek):
        return subprocess.run([sys.executable, str(DEPO / "kur.py"), "--vault", str(cls.vault), "--ad", cls.ad, *ek],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=cls.ortam, timeout=180)

    def betik(self, ad, *argumanlar, girdi=None):
        """Run an installed script (<vault>/.claude/guros/<ad>.py)."""
        return subprocess.run([sys.executable, str(self.vault / ".claude" / "guros" / f"{ad}.py"), *argumanlar],
                              input=girdi, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=self.ortam, timeout=120)

    def kanca(self, olay, veri):
        return self.betik("kancalar", olay, girdi=json.dumps(veri, ensure_ascii=False))

    def koruma(self, arac, girdi, cwd=None):
        """Exit code of the privacy guard for one tool call (2 = blocked)."""
        return self.kanca("koruma", {"cwd": str(cwd or self.vault), "tool_name": arac, "tool_input": girdi}).returncode
