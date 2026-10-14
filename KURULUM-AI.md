# KURULUM-AI — yapay zekâ asistanları için kurulum talimatı

> **English summary for agents:** The user wants GurOS (an Obsidian second-brain memory layer) installed, updated
> or removed. Follow the steps below. List their vaults with `kur.py --vaultlar`, ask the three questions in one
> message, run `kur.py` **without** `--uygula` first and show the plan (including any private-folder warning),
> apply only after an explicit yes, then report the health check. Talk to the user in their language (usually
> Turkish). Never open their notes or private folders; never ask for passwords or keys.

Bu dosyayı okuyorsan kullanıcı büyük olasılıkla bu depoyu sana verip "bu sistemi bana kur" dedi.
Aşağıdaki adımları sırayla izle ve kullanıcıyla onun dilinde konuş.

## Kurallar

1. **Planı göstermeden kurma.** `kur.py` önce `--uygula` olmadan çalışır ve yalnızca plan basar. Planı
   kullanıcıya göster. Açık bir "evet" gelmeden `--uygula` çalıştırma.
2. **Notları okuma, değiştirme.** Kurulum için vault'un içeriğine bakman gerekmez; klasör adları yeter.
   Var olan notları kurulum aracı da ezmez.
3. **Özel klasörlere girme.** Günlük ya da özel klasörlerin içini açma, listeleme, arama. Yalnızca adlarını
   `--ozel` ile ver.
4. **Sır isteme.** Kurulum hiçbir parola, token ya da API anahtarı gerektirmez.
5. **Kullanıcının yerine yazılım kurma.** Python ya da Claude Code eksikse komutu göster ve kullanıcıya sor.
   Sistem ayarlarını değiştirme.

## En kısa yol: tek satırlık kurulum

Kullanıcı kendi terminalinde çalıştırmak isterse ona şu satırı ver. Bu komut Python'u bulur, paketi indirir ve
soru soran sihirbazı açar. Sihirbaz etkileşimli olduğu için bunu **kullanıcı** çalıştırmalı, sen değil.

- Windows (PowerShell): `irm https://raw.githubusercontent.com/guraygur0/guros-ikinci-beyin/main/kur.ps1 | iex`
- macOS / Linux: `curl -fsSL https://raw.githubusercontent.com/guraygur0/guros-ikinci-beyin/main/kur.sh | bash`

Kurulumu senin yapmanı istiyorsa aşağıdaki adımları izle.

## 1. Ortamı kontrol et

```bash
python --version      # Windows (olmazsa: py -3 --version)
python3 --version     # macOS / Linux
```

Python 3.9 veya üstü gerekir. Yoksa kullanıcıya göster ve onay iste:

- Windows: `winget install -e --id Python.Python.3.12 --scope user`, ya da https://www.python.org/downloads/
  ("Add python.exe to PATH" işaretli).
- macOS: `brew install python`, ya da python.org.
- Linux: `sudo apt install python3` (Fedora: `dnf`, Arch: `pacman`).

`python` komutu Windows'ta Microsoft Store'u açıyorsa bu gerçek Python değildir; python.org sürümünü öner.

## 2. Depoyu indir

Depoyu vault'un **dışına** indir; ev klasörü uygundur. Paket vault'un içindeyse kurulum aracı reddeder.

```bash
git clone https://github.com/guraygur0/guros-ikinci-beyin.git ~/guros-ikinci-beyin
```

git yoksa ZIP olarak indir:

- Windows PowerShell:
  ```powershell
  Invoke-WebRequest https://github.com/guraygur0/guros-ikinci-beyin/archive/refs/heads/main.zip -OutFile "$HOME\guros.zip"
  Expand-Archive "$HOME\guros.zip" -DestinationPath "$HOME"
  Rename-Item "$HOME\guros-ikinci-beyin-main" guros-ikinci-beyin
  ```
- macOS / Linux:
  ```bash
  curl -L https://github.com/guraygur0/guros-ikinci-beyin/archive/refs/heads/main.tar.gz | tar -xz -C ~
  mv ~/guros-ikinci-beyin-main ~/guros-ikinci-beyin
  ```

Depo zaten indirilmişse güncelle (`git -C ~/guros-ikinci-beyin pull`) ya da bu adımı atla.

## 3. Vault'ları bul ve kullanıcıya sor

Önce bilgisayardaki Obsidian vault'larını listele. Bu komut yalnızca Obsidian'ın kendi listesini okur:

```bash
python ~/guros-ikinci-beyin/kur.py --vaultlar
```

Sonra aşağıdakileri **tek mesajda** sor ve varsayılanları da yaz:

1. **Hangi vault?** Bulunanlardan biri ya da yeni bir klasör (örnek: `~/Documents/GurOS`).
2. **Adın ne?** Asistan sana bu adla hitap eder.
3. **Hangi klasörler yapay zekâya kapalı kalsın?** Varsayılan: yeni bir `🔒 Özel Alan` klasörü. Planda adından
   özel olduğu anlaşılan klasörler listelenir (4. adım); onları da sor.

İsteğe bağlı: asistanın adı (varsayılan `Logos`), günlük bakım (varsayılan hayır).

## 4. Planı çıkar ve göster

```bash
python ~/guros-ikinci-beyin/kur.py --vault "<vault yolu>" --ad "<ad>"
```

- macOS/Linux'ta `python3` kullan.
- Her kapalı klasör için ayrı `--ozel "<klasör>"` ver. Verdiğin liste varsayılanın yerine geçer; `🔒 Özel Alan`
  da isteniyorsa onu da ekle.
- Asistanın adı için `--asistan "<ad>"` ekle.

Planı gruplar halinde özetle: Notlar, Hafıza, Asistan kuralları, Claude Code, Sistem. Şunları özellikle söyle:

- Var olan hiçbir not ezilmez.
- `CLAUDE.md` zaten varsa metnine dokunulmaz.
- `.claude/settings.json` değişmeden önce yedeklenir.

Plan sonunda `!` ile başlayan bir uyarı varsa (ör. *"Adından özel olduğu anlaşılan klasörler yapay zekâya AÇIK
kalacak"*), bunu kullanıcıya mutlaka sor ve uyarıdaki bayraklarla planı yeniden çıkar. `✗` satırı varsa önce onu çöz.

## 5. Onay gelince kur

Aynı komutu sonuna `--uygula` ekleyerek çalıştır. Günlük bakım istendiyse `--zamanla --saat 10:00` ekle.

Çıktının sonundaki "Sağlık kontrolü" bölümünde `Sonuç: 0 hata` görmelisin. Hata varsa satırı oku ve düzelt.
Kontrolü sonradan yeniden çalıştırmak için:

```bash
python "<vault yolu>/.claude/guros/doktor.py"
```

## 6. Kullanıcıya sonraki adımları söyle

1. Obsidian'da vault klasörünü aç: **Open folder as vault**.
2. Claude Code'u **vault klasörünün içinde** başlat: `cd "<vault yolu>"`, sonra `claude`.
   - İlk açılışta **"Do you trust the files in this folder?"** sorusuna **Yes** demeli. Kancalar ve izinler ancak
     bu onaydan sonra çalışır.
   - Sen şu an başka bir klasörde çalışan bir Claude Code oturumuysan bunu özellikle söyle: kancalar yalnızca
     vault'ta açılan yeni bir oturumda yüklenir.
3. Codex kullanıyorsa vault klasöründe `codex` başlatsın; kuralları `AGENTS.md` dosyasından okur.
4. "merhaba" desin. Asistan kendini tanıtır ve onu tanımak için sorular sorar. Vault'taki `👋 Başlarken` notu
   kullanımı anlatır.
5. Claude Code yüklü değilse kurulum çıktısındaki resmi komutu göster: Windows'ta
   `irm https://claude.ai/install.ps1 | iex`, macOS/Linux'ta `curl -fsSL https://claude.ai/install.sh | bash`.
   Ücretli bir Claude hesabı gerekir.

## Güncelleme ve kaldırma

- **Güncelleme:** depoyu güncelle (`git pull`), sonra `kur.py --vault "<vault yolu>" --uygula`. Önceki ad ve özel
  klasörler `ayarlar.json`'dan okunur; yalnızca sistem kodu, kurallar ve kancalar yenilenir.
- **Kaldırma:** önce `kur.py --vault "<vault yolu>" --kaldir` ile planı göster, onay gelince `--uygula` ekle.
  Kancalar, komutlar, sistem kodu ve GurOS kural bloğu çıkar; notlar, hafıza klasörü ve özel klasörlerin izin
  kuralları kalır.

## Komut çalıştıramıyorsan

Tarayıcıdaki bir sohbet aracıysan kullanıcıya en kısa yolu ver: yukarıdaki tek satırlık komutu PowerShell'e
(Windows) ya da Terminal'e (macOS/Linux) yapıştırsın. Sihirbaz gerisini sorar. Bir hata çıkarsa çıktıyı
yapıştırmasını iste ve birlikte ilerleyin.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `python` bulunamadı | Windows: `py -3 kur.py ...`. macOS/Linux: `python3`. |
| `.claude/settings.json geçerli JSON değil` | Dosyadaki yazım hatasını kullanıcıyla düzelt; kurulum dosyaya dokunmadı. |
| Doktor "kancaların Python yolu yok" diyor | Python taşınmış ya da silinmiş. `kur.py --uygula` ile yeniden kur. |
| Doktor "Claude Code … eski" diyor | `claude update` çalıştırılmalı; kancalar 2.1.139 ve üstünü ister. |
| Açılışta bağlam gelmiyor | Claude Code vault klasöründe mi başlatıldı, güven sorusuna Yes denildi mi? `/doktor` çalıştır. |
| Özel klasör listesi yanlış | `kur.py --vault "<vault yolu>" --ozel "<klasör>" ... --uygula` ile doğru listeyle yeniden kur. |
