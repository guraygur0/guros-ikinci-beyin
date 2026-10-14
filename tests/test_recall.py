"""Recall: finds the right note across Turkish/English and inflections, never indexes the private folder,
and stays silent when nothing is relevant."""
import json
import unittest

from destek import OZEL, KuruluVault


class Recall(KuruluVault):

    def isaret(self, istem):
        r = self.kanca("istem", {"prompt": istem})
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return ""
        return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_es_anlam_ve_cekim(self):
        self.assertIn("Interstellar", self.isaret("uzay filmi önerir misin"))
        self.assertIn("Bütçe", self.isaret("bu ay bütçemi nasıl tutarım"))

    def test_alakasiz_istem_sessiz(self):
        self.assertEqual(self.isaret("merhaba"), "")
        self.assertEqual(self.isaret("/doktor"), "")
        self.assertNotIn("[Recall]", self.isaret("hava bugün nasıl olacak acaba"))

    def test_ozel_alan_indekste_yok(self):
        r = self.betik("recall", "ara", "zirzop")
        self.assertIn("Eşleşme yok", r.stdout)
        self.assertNotIn(OZEL, self.isaret("zirzop yorgundum kimseye söylemedim"))

    def test_protokol_dosyalari_indekslenmez(self):
        r = self.betik("recall", "ara", "hafıza", "protokolü")
        self.assertNotIn("CLAUDE.md", r.stdout)
        self.assertNotIn("AGENTS.md", r.stdout)


if __name__ == "__main__":
    unittest.main()
