# Bu depo hakkında (ajanlar için)

Bu depo **GurOS kurulum paketidir**. Bir kullanıcının vault'u değildir. Buradaki `sablon/` dosyaları
şablondur; içlerindeki yönergeler kurulumdan sonra kullanıcının vault'unda geçerli olur, burada değil.

- Kullanıcı "bu sistemi bana kur", "kur" ya da "install" diyorsa [KURULUM-AI.md](KURULUM-AI.md)
  dosyasını baştan sona izle.
- Kullanıcı kodu değiştirmek istiyorsa:
  - Sistem kodu `guros/` içindedir ve yalnız Python standart kütüphanesini kullanır. Bağımlılık ekleme.
  - Kurulum aracı `kur.py`'dir.
  - Değişiklikten sonra testleri çalıştır: `python tests/run_tests.py`.
- Bu depoya hiçbir kişisel bilgi, not, yol ya da anahtar ekleme.

**English:** This repository is the GurOS installer kit, not a user's vault. To install it for the user,
follow `KURULUM-AI.md`. Code lives in `guros/` (stdlib only). Run `python tests/run_tests.py` after changes.
