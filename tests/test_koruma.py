"""Privacy guard: everything that names or sweeps the private folder is blocked; ordinary work is not."""
import unittest

from destek import OZEL, KuruluVault


class Koruma(KuruluVault):

    def engellenir(self, arac, girdi, **kw):
        self.assertEqual(self.koruma(arac, girdi, **kw), 2, f"engellenmeliydi: {arac} {girdi}")

    def serbest(self, arac, girdi, **kw):
        self.assertEqual(self.koruma(arac, girdi, **kw), 0, f"serbest olmalıydı: {arac} {girdi}")

    def test_adiyla_erisim(self):
        self.engellenir("Read", {"file_path": f"{OZEL}/gunluk.md"})
        self.engellenir("Read", {"file_path": str(self.vault / OZEL / "gunluk.md")})
        self.engellenir("Read", {"file_path": str(self.vault / "Filmler" / ".." / OZEL / "gunluk.md")})
        self.engellenir("Edit", {"file_path": f"{OZEL}/gunluk.md", "old_string": "a", "new_string": "b"})
        self.engellenir("Write", {"file_path": f"{OZEL}/yeni.md", "content": "x"})
        self.engellenir("Bash", {"command": f'cat "{OZEL}/gunluk.md"'})
        self.engellenir("Bash", {"command": "cat ozel_alan/gunluk.md"})          # spacing and case ignored
        self.engellenir("Bash", {"command": "cat '\U0001F512 ÖZEL ALAN'/*"})
        self.engellenir("PowerShell", {"command": f"Get-Content '{OZEL}\\gunluk.md'"})

    def test_joker_ile_erisim(self):
        self.engellenir("Glob", {"pattern": "**/*Özel*/**"})
        self.engellenir("Glob", {"pattern": "**/*.md"})
        self.engellenir("Glob", {"pattern": "*/*"})
        self.engellenir("Bash", {"command": "cat */*.md"})
        self.engellenir("Bash", {"command": "head -n 3 **/*.md"})
        self.engellenir("Bash", {"command": "ls *"})
        self.engellenir("Bash", {"command": "cat *Özel*/*"})

    def test_ozyinelemeli_arama(self):
        self.engellenir("Grep", {"pattern": "yorgun"})
        self.engellenir("Grep", {"pattern": "yorgun", "glob": "*.md"})
        self.engellenir("Grep", {"pattern": "yorgun", "path": str(self.vault)})
        self.engellenir("Bash", {"command": "ls Filmler && grep -r yorgun ."})
        self.engellenir("Bash", {"command": "grep -rn yorgun"})
        self.engellenir("Bash", {"command": "rg yorgun -g '*.md'"})
        self.engellenir("Bash", {"command": "find . -name '*.md'"})
        self.engellenir("Bash", {"command": "cp -r . ../kopya"})
        self.engellenir("Bash", {"command": f"grep -r yorgun {self.tmp.as_posix()}"})      # a folder above the vault
        self.engellenir("PowerShell", {"command": "Get-ChildItem -Recurse -Filter *.md | Select-String yorgun"})
        self.engellenir("PowerShell", {"command": "gci -r | sls yorgun"})

    def test_siradan_is_serbest(self):
        self.serbest("Read", {"file_path": "Filmler/Interstellar.md"})
        self.serbest("Edit", {"file_path": "Filmler/Interstellar.md", "old_string": "a", "new_string": "özel alan"})
        self.serbest("Glob", {"pattern": "Filmler/*.md"})
        self.serbest("Glob", {"pattern": "**/*Interstellar*"})
        self.serbest("Glob", {"pattern": "*"})
        self.serbest("Grep", {"pattern": "uzay", "path": "Filmler"})
        self.serbest("Grep", {"pattern": "uzay", "glob": "Filmler/**"})
        self.serbest("Bash", {"command": "ls -la"})
        self.serbest("Bash", {"command": "cat *.md"})
        self.serbest("Bash", {"command": "grep -rn uzay Filmler"})
        self.serbest("Bash", {"command": "cd Filmler && grep -r uzay ."})
        self.serbest("Bash", {"command": "find Filmler -name '*.md'"})
        self.serbest("Bash", {"command": "git status && git log -3"})
        self.serbest("Bash", {"command": "python .claude/guros/recall.py ara uzay filmi"})
        self.serbest("PowerShell", {"command": "Get-ChildItem -Path Filmler -Recurse"})

    def test_vault_disinda_serbest(self):
        baska = self.tmp / "baska-proje"
        baska.mkdir(exist_ok=True)
        self.serbest("Bash", {"command": "grep -r foo ."}, cwd=baska)
        self.serbest("Grep", {"pattern": "foo"}, cwd=baska)
        self.serbest("Glob", {"pattern": "**/*.py"}, cwd=baska)

    def test_bozuk_girdi_kilitlemez(self):
        r = self.betik("kancalar", "koruma", girdi="bu json değil")
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
