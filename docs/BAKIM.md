# Bakım, yedek ve sorun giderme

## Günlük bakım

`bakim.py` güvenli bir şekilde istendiği zaman çalıştırılabilir. Üç iş yapar:

1. Recall indeksini sıfırdan kurar.
2. Doktoru sessiz modda çalıştırır.
3. Yedek kuruluysa yedekler.

Sonucu durum klasöründeki `bakim.log` dosyasına bir satır olarak yazar: `~/.guros/<vault>-<iz>/bakim.log`.

Kurarken zamanlamak için:

```bash
python kur.py --vault "<vault>" --ad "<ad>" --uygula --zamanla --saat 10:00
```

- **Windows.** Görev Zamanlayıcı'ya `GurOS Bakim - <vault adı>` adlı günlük bir görev eklenir.
  Görev `pythonw` ile pencere açmadan çalışır.
- **macOS / Linux.** `crontab`'a bir satır eklenir. Satırın sonunda `# GurOS` yazar.

Elle çalıştırmak için:

```bash
python "<vault>/.claude/guros/bakim.py"
```

## Yedek

Yedek isteğe bağlıdır ve git ile çalışır. Vault'u **özel** bir depoya gönderir.

1. GitHub'da yeni bir depo aç ve görünürlüğünü **Private** seç.
2. Vault klasöründe şunu çalıştır:

```bash
python .claude/guros/yedek.py --kur https://github.com/<kullanıcı>/<özel-repo>.git
python .claude/guros/yedek.py           # şimdi yedekle
python .claude/guros/yedek.py --durum   # son yedek ne zaman
```

Yedek kodu şu kuralları uygular:

- Özel klasörler `.gitignore`'a yazılır. Git bir özel dosyayı izliyorsa yedek durur ve
  `git rm -r --cached "<klasör>"` komutunu önerir. Bu komut dosyayı diskten silmez, yalnızca izlemeden çıkarır.
- Her commit'ten önce eklenen satırlar taranır. Aranan desenler: API anahtarı (OpenAI, Anthropic,
  Google, AWS), GitHub ve Slack token'ı, Telegram bot token'ı, özel anahtar bloğu, `password = ...`
  biçiminde atamalar. Tek bir eşleşme varsa commit atılmaz ve dosya ile sır türü gösterilir.
- Zorla push yapılmaz. Uzak depo ilerlemişse karar senindir.

Telefonla eşitleme (Obsidian Sync, Syncthing, iCloud…) ile git yedeği birlikte çalışır. Eşitleme
cihazlar arasında taşır, git geçmişi tutar.

## Güncelleme

En kolayı kurulum komutunu yeniden çalıştırmak:

- Windows: `irm https://raw.githubusercontent.com/guraygur0/guros-ikinci-beyin/main/kur.ps1 | iex`
- macOS / Linux: `curl -fsSL https://raw.githubusercontent.com/guraygur0/guros-ikinci-beyin/main/kur.sh | bash`

Bu komut paketi günceller ve sihirbazı açar. Sihirbaz kurulu sistemi tanır; **Güncelle**'yi seç.

Elle güncellemek istersen:

```bash
cd guros-ikinci-beyin
git pull
python kur.py --vault "<vault>" --uygula
```

Yeniden kurulum şunları yeniler:

- `.claude/guros/` altındaki kod,
- `CLAUDE.md` ve `AGENTS.md` içindeki GurOS bloğu,
- kancalar ve izin kuralları.

Notlara, hafıza dosyalarına, ayarlarına (`ayarlar.json`) ve kendi eklediğin komutlara dokunmaz.
`CLAUDE.md` içinde `<!-- GUROS:PROTOKOL -->` bloğunun dışına yazdıkların korunur. Bir bayrak verirsen (ör.
`--ozel`), o değer `ayarlar.json`'daki eskisinin yerine geçer.

## Ayarlar

`.claude/guros/ayarlar.json`:

| Alan | Varsayılan | Anlamı |
|---|---|---|
| `ad` | — | Sana hitap edilen ad |
| `asistan` | Logos | Asistanın adı |
| `hafiza_klasoru` | 🔮 Logos | Hafıza klasörü |
| `proje_klasoru` | Projeler | Proje notları |
| `ozel_klasorler` | ["🔒 Özel Alan"] | Yapay zekâya kapalı klasörler (vault'a göre yol) |
| `hatirlatma_esigi` | 10 | Hafızaya yazılmadan geçebilecek mesaj sayısı |
| `recall_sonuc` | 3 | Her mesajda en fazla kaç işaretçi |
| `baglam_siniri` | 6000 | Açılış bağlamının en fazla karakter sayısı |

Değiştirdikten sonra `kur.py --uygula` ile yeniden kur. Protokol metni ve izin kuralları yeni
değerlerle yazılır.

## Kaldırma

```bash
python kur.py --vault "<vault>" --kaldir           # plan
python kur.py --vault "<vault>" --kaldir --uygula  # uygula
```

Sihirbazdan da kaldırabilirsin: kurulum komutunu yeniden çalıştır ve **Kaldır**'ı seç.

Kaldırma şunları yapar:

- kancaları ve GurOS izinlerini `settings.json`'dan çıkarır (senin eklediğin kurallar kalır),
- GurOS komutlarını ve `.claude/guros/` klasörünü siler, zamanlanmış görevi kaldırır,
- `CLAUDE.md` ve `AGENTS.md` içinden GurOS bloğunu çıkarır. Blok dışında metin yoksa dosya silinir; varsa o metne
  dokunulmaz.

Notların, hafıza klasörün ve özel klasörlerin yerinde kalır. Özel klasörlerin izin kuralları da koruma olarak kalır.

## Sorun giderme

İlk adım her zaman sağlık kontrolüdür: `/doktor` ya da `python .claude/guros/doktor.py`.

| Belirti | Neden ve çözüm |
|---|---|
| Açılışta bağlam gelmiyor | Claude Code vault klasöründe başlatılmamış ya da "Do you trust the files in this folder?" sorusuna Yes denmemiş. Kancalar yalnızca başlatılan ve güvenilen klasörün `.claude/settings.json` dosyasından yüklenir. |
| Asistan hafızaya her yazışta izin soruyor | Klasöre güven onayı verilmemiş ya da kurulum 1.0.0'dan kalma. Yeniden kur; güven sorusuna Yes de. |
| "kancaların Python yolu yok" | Kurulumda kullanılan Python taşındı ya da silindi. `kur.py --uygula` ile yeniden kur. |
| Asistan vault genelinde arama yapamıyor | Bu bilerek böyledir: kökten özyinelemeli arama özel klasöre de girer. Recall'u (`/recall`) kullan ya da aramayı bir alt klasöre daralt. |
| Recall ilgili notu bulmuyor | `python .claude/guros/recall.py kur` ile indeksi yeniden kur. Kelime eş anlamlı bir sözcükse `es_anlamlar.json` dosyasına grup ekle. |
| Stop kancası çok sık hafıza istiyor | `hatirlatma_esigi` değerini büyüt. |
| Windows'ta Türkçe karakterler bozuk | Python 3.9+ ve UTF-8 terminal kullan. GurOS kendi çıktısını UTF-8'e zorlar. |
| `sync-conflict` dosyaları | Aynı notu iki cihaz aynı anda düzenledi. GurOS notları yeniden yazmak yerine sonlarına ekleyerek bunu azaltır. Çakışma dosyasını sen gözden geçirip sil. |
