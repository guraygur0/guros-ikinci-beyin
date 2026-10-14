"""Backup: private folders never reach git, a secret-looking line stops the commit, a clean change is pushed."""
import shutil
import subprocess
import unittest

from destek import OZEL, KuruluVault, yaz


@unittest.skipUnless(shutil.which("git"), "git yok")
class Yedek(KuruluVault):

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-c", "core.quotepath=false", "-C", str(cwd or self.vault), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def test_yedek_akisi(self):
        uzak = self.tmp / "uzak.git"
        subprocess.run(["git", "init", "-q", "--bare", str(uzak)], check=True)
        r = self.betik("yedek", "--kur", uzak.as_posix())
        self.assertEqual(r.returncode, 0, r.stderr)

        # 1) a secret-looking line: nothing is committed
        yaz(self.vault / "Finans" / "anahtar.md", "api_key = sk-ant-" + "x" * 40 + "\n")
        r = self.betik("yedek")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("sır", r.stderr)
        self.assertNotEqual(self.git("rev-parse", "HEAD").returncode, 0, "sır varken commit atıldı")

        # 2) clean: committed and pushed, private folder left out
        (self.vault / "Finans" / "anahtar.md").unlink()
        r = self.betik("yedek")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dosyalar = self.git("ls-tree", "-r", "--name-only", "main", cwd=uzak).stdout.splitlines()
        self.assertIn("Filmler/Interstellar.md", dosyalar)
        self.assertFalse([d for d in dosyalar if d.startswith(OZEL)], "özel klasör yedeğe girdi")

        # 3) a private file that git already tracks (e.g. the folder became private later) stops the backup
        self.git("add", "-f", f"{OZEL}/gunluk.md")
        r = self.betik("yedek")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("git rm -r --cached", r.stderr)
        self.assertNotIn(f"{OZEL}/gunluk.md", self.git("ls-tree", "-r", "--name-only", "main", cwd=uzak).stdout)


if __name__ == "__main__":
    unittest.main()
