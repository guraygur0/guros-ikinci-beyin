# KURULUM-AI — yapay zekâ asistanları için kurulum talimatı

> **English summary for agents:** The user wants GurOS (an Obsidian second-brain memory layer)
> installed. Follow the steps below. Ask the three questions, run `kur.py` **without** `--uygula`
> first and show the plan, apply only after the user says yes, then run the health check. Talk to the
> user in their language (most users write Turkish). Never read or modify their existing notes beyond
> what the installer does. Never ask for passwords or keys.

Bu dosyayı okuyorsan kullanıcı büyük olasılıkla bu depoyu sana verip "bu sistemi bana kur" dedi.
Aşağıdaki adımları sırayla izle. Kullanıcıyla onun dilinde konuş.

## Kurallar

1. **Planı göstermeden kurma.** `kur.py` önce `--uygula` olmadan çalışır ve yalnızca plan basar.
   Planı kullanıcıya göster. Açık bir "evet" gelmeden `--uygula` çalıştırma.
2. **Kullanıcının notlarını okuma, değiştirme.** Kurulum için vault'un içeriğine bakman gerekmez.
   Yalnızca klasörün var olup olmadığını ve klasör adlarını kontrol edebilirsin.
3. **Özel klasöre girme.** Kullanıcının günlüğü ya da özel klasörü varsa içini açma.
   Yalnızca adını `--ozel` ile ver.
4. **Sır isteme.** Kurulum hiçbir parola, token ya da API anahtarı gerektirmez.
5. **Kendi başına kurulum yapma.** Python, git ya da Obsidian eksikse kullanıcıya nereden
   kuracağını söyle. Kurulumu o yapsın. Sistem ayarlarını değiştirme.

## 1. Ortamı kontrol et

```bash
python --version      # Windows (olmazsa: py -3 --version)
python3 --version     # macOS / Linux
git --version         # isteğe bağlı
```

- Python 3.9 veya üstü gerekir. Yoksa kullanıcıyı https://www.python.org/downloads/ adresine yönlendir.
  Windows'ta kurulumda "Add python.exe to PATH" seçilmeli.
- Windows'ta `python` komutu Microsoft Store'u açıyorsa Store sürümü değil, python.org sürümü önerilir.
- git yoksa sorun değil. Depoyu ZIP olarak indirebilirsin (2. adım).

## 2. Kullanıcıya sor

Aşağıdakileri **tek mesajda** sor. Varsayılanları da yaz ki kullanıcı "varsayılan olsun" diyebilsin.

1. **Vault klasörü nerede?** Var olan bir Obsidian vault'unun tam yolu ya da oluşturulacak yeni
   bir klasör. Örnek: `C:\Users\<ad>\Documents\Vault`, `~/Documents/Vault`.
2. **Adın ne?** Asistan sana bu adla hitap eder.
3. **Hangi klasör yapay zekâya kapalı kalsın?** Varsayılan `🔒 Özel Alan` (yeni oluşturulur).
   Vault'unda günlük ya da özel bir klasör varsa onun adını ver.

İsteğe bağlı sorular:

- Asistanın adı. Varsayılan `Logos`.
- Günlük bakım zamanlansın mı. Varsayılan hayır.

Kullanıcı vault'un yerini bilmiyorsa Obsidian'da sol alttaki vault adına tıklayıp "Manage vaults"
penceresinde yolu görebileceğini söyle.

## 3. Depoyu indir

Depoyu vault'un **dışına** indir. Ev klasörü uygundur.

```bash
git clone https://github.com/guraygur0/guros-ikinci-beyin.git ~/guros-ikinci-beyin
```

git yoksa ZIP'i indirip aç:

- Windows PowerShell:
  ```powershell
  Invoke-WebRequest https://github.com/guraygur0/guros-ikinci-beyin/archive/refs/heads/main.zip -OutFile "$HOME\guros.zip"
  Expand-Archive "$HOME\guros.zip" -DestinationPath "$HOME"
  Rename-Item "$HOME\guros-ikinci-beyin-main" guros-ikinci-beyin
  ```
- macOS / Linux:
  ```bash
  curl -L -o ~/guros.zip https://github.com/guraygur0/guros-ikinci-beyin/archive/refs/heads/main.zip
  unzip ~/guros.zip -d ~ && mv ~/guros-ikinci-beyin-main ~/guros-ikinci-beyin
  ```

Kullanıcı depoyu zaten indirmişse ve sen o klasördeysen bu adımı atla.

## 4. Planı çıkar ve göster

```bash
cd ~/guros-ikinci-beyin
python kur.py --vault "<vault yolu>" --ad "<ad>" --ozel "<özel klasör>"
```

- macOS/Linux'ta `python3` kullan.
- Varsayılan dışında asistan adı istendiyse `--asistan "<ad>"` ekle.
- `--ozel` birden çok kez verilebilir.

Çıktıdaki `[PLAN]` satırlarını kullanıcıya özetle: hangi dosyalar eklenecek, hangi ayarlar
birleştirilecek. Özellikle şunları belirt:

- Var olan hiçbir not ezilmez.
- `CLAUDE.md` zaten varsa metnine dokunulmaz. Protokol `CLAUDE.guros.md` dosyasına yazılır.
- `.claude/settings.json` değişmeden önce yedeklenir.

`[EKSİK]` satırı varsa önce onu çöz.

## 5. Onay gelince kur

```bash
python kur.py --vault "<vault yolu>" --ad "<ad>" --ozel "<özel klasör>" --uygula
```

Günlük bakım istendiyse `--zamanla --saat 10:00` ekle.

Çıktının sonundaki doğrulama bölümünde `Sonuç: 0 hata` görmelisin. Hata varsa satırı oku ve düzelt.
Gerekirse sağlık kontrolünü yeniden çalıştır:

```bash
python "<vault yolu>/.claude/guros/doktor.py"
```

## 6. Kullanıcıya sonraki adımları söyle

1. Obsidian'da vault klasörünü aç: "Open folder as vault".
2. Claude Code'u **vault klasörünün içinde** başlat: `cd "<vault yolu>"`, sonra `claude`.
   Kancalar yalnızca böyle yüklenir. Sen şu an başka bir klasörde çalışan bir Claude Code
   oturumuysan bunu özellikle söyle: yeni bir oturum açması gerekir.
3. Codex kullanıyorsa vault klasöründe `codex` başlatsın. Codex `AGENTS.md` dosyasını okur.
4. İlk sohbette "merhaba" desin. Asistan kendini tanıtır ve onu tanımak için sorular sorar.
5. İsteğe bağlı yedek, **özel** bir GitHub deposuna:
   `python .claude/guros/yedek.py --kur https://github.com/<kullanıcı>/<özel-repo>.git`.

Kurulumun özeti için `README.md` dosyasının "Neler kurulur" bölümünü kullanabilirsin.

## Komut çalıştıramıyorsan

Tarayıcıdaki bir sohbet aracıysan ve komut çalıştıramıyorsan kullanıcıya şu adımları anlat:

1. Python'u kurmasını söyle.
2. Bu sayfadaki **Code → Download ZIP** ile indirip açmasını söyle.
3. Terminali o klasörde açmasını söyle.
   - Windows: klasörde boş bir yere Shift + sağ tık, sonra "Terminalde aç".
   - macOS: Finder'da klasöre sağ tık, sonra "Klasörde Yeni Terminal".
4. 4. ve 5. adımlardaki komutları yolunu ve adını yerleştirerek ver.

Her komuttan sonra çıktıyı yapıştırmasını iste ve birlikte ilerleyin.

## Sorun giderme

| Belirti | Çözüm |
|---|---|
| `python` bulunamadı | Windows: `py -3 kur.py ...`. macOS/Linux: `python3`. |
| `.claude/settings.json geçerli JSON değil` | Dosyadaki yazım hatasını kullanıcıyla düzelt; kurulum dosyaya dokunmadı. |
| Doktor "kancaların Python yolu yok" diyor | Python taşınmış ya da sanal ortam silinmiş. `kur.py --uygula` komutunu yeniden çalıştır. |
| Açılışta bağlam gelmiyor | Claude Code vault klasöründe mi başlatıldı? `/doktor` çalıştır. |
| Özel klasör yanlış | `.claude/guros/ayarlar.json` dosyasında `ozel_klasorler` alanını düzelt ve `kur.py --uygula` komutunu yeniden çalıştır. |
