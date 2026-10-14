# GurOS — Obsidian için yapay zekâ ikinci beyin

Obsidian vault'unu, seni hatırlayan bir yapay zekâ ortağına dönüştürür. Asistan her sohbete
hedeflerini, projelerini ve geçen oturumda kaldığın yeri bilerek başlar. Öğrendiklerini kendi
hafıza klasörüne yazar ve senin özel klasörüne giremez.

- **Kalıcı hafıza.** Kim olduğun, kararların, süren işlerin ve biten oturumların özeti düz Markdown
  notlarda durur. Hepsi senin vault'unda, Obsidian'da okunabilir.
- **Otomatik bağlam.** Her sohbetin başında açık hedefler, projelerin sıradaki adımı, süren işler
  ve son oturum asistana kendiliğinden verilir.
- **Yerel arama (Recall).** Her mesajda vault'unda ilgili notlar bulunur ve asistana işaret edilir.
  Türkçe çekim ekleri ile Türkçe–İngilizce eş anlamlılar tanınır: "uzay filmi" araması `Filmler/Interstellar`
  notunu bulur. Bu arama için model ya da internet gerekmez.
- **Gizlilik koruması.** Günlük gibi özel bir klasörü asistana tamamen kapatırsın. Okuma, arama
  ve kabuk komutlarıyla dolanma engellenir.
- **Unutmaz.** Uzun bir sohbette bir süre hafızaya hiçbir şey yazılmazsa sistem asistanı durdurup
  yazmasını ister.
- **Notlarına saygılı.** Kurulum hiçbir notunu ezmez, iki kez çalıştırılabilir. Asistanın
  kuralları var olan notlarını sormadan değiştirmeyi yasaklar.

Yalnız Python standart kütüphanesi kullanılır, kurulacak paket yoktur. Windows, macOS ve Linux'ta çalışır.
**Claude Code** ile her parçası çalışır. **Codex**, Cursor ve diğer ajanlar aynı protokolü `AGENTS.md`
üzerinden okur; otomatik kancalar bu araçlarda çalışmaz (ayrıntı aşağıda).

---

## 🤖 En kolay kurulum: yapay zekâna kurdur

Komut çalıştırabilen bir yapay zekâ aracı aç: Claude Code, Codex ya da Cursor'un ajan modu.
Sonra şunu yaz:

```
https://github.com/guraygur0/guros-ikinci-beyin
bu sistemi bana kur
```

Asistan şunları yapar:

1. Sana üç şey sorar: vault'un nerede, adın ne, hangi klasör özel kalsın.
2. Kurulum planını gösterir. Bu aşamada hiçbir şey yazılmaz.
3. Sen onaylayınca kurar ve sağlık kontrolünü çalıştırır.

Asistanların izlediği adımlar [KURULUM-AI.md](KURULUM-AI.md) dosyasında.

> Komut çalıştıramayan bir sohbet aracı da (ör. tarayıcıdaki sohbet) bu sayfayı okuyup sana adım adım
> elle kurulumu anlatabilir.

## 🛠 Elle kurulum

**Gerekenler:**
- [Python 3.9+](https://www.python.org/downloads/). Windows'ta kurarken "Add python.exe to PATH" kutusunu işaretle.
- [Obsidian](https://obsidian.md).
- [Claude Code](https://code.claude.com/docs/en/overview). Codex gibi başka bir ajan da olur.
- git, yalnızca isteğe bağlı yedek için.

**1. İndir.** Kodu vault'unun **dışına** indir.

```bash
git clone https://github.com/guraygur0/guros-ikinci-beyin.git
```

git yoksa sayfanın üstündeki **Code → Download ZIP** ile indirip bir klasöre aç.

**2. Planı gör.** Bu adım hiçbir şey yazmaz.

```bash
cd guros-ikinci-beyin
python kur.py --vault "C:\Users\sen\Belgeler\Vault" --ad "Ayşe"
```

macOS/Linux'ta `python` yerine `python3` yaz. Vault klasörü yoksa oluşturulur. Varsa notlarına dokunulmaz.

**3. Kur.** Aynı komutu sonuna `--uygula` ekleyerek çalıştır.

```bash
python kur.py --vault "C:\Users\sen\Belgeler\Vault" --ad "Ayşe" --uygula
```

**4. Başla.** Klasörü Obsidian'da vault olarak aç. Sonra Claude Code'u **vault klasörünün içinde** başlat:

```bash
cd "C:\Users\sen\Belgeler\Vault"
claude
```

Merhaba de. Hafıza boşsa asistan kendini tanıtır ve seni tanımak için birkaç soru sorar.

> ⚠️ Claude Code proje ayarlarını (kancalar dahil) başladığı klasörden okur. Başka bir klasörde açarsan
> hafıza kancaları ve gizlilik koruması devreye girmez. Her zaman vault'un içinde başlat.

### Seçenekler

| Seçenek | Varsayılan | Ne işe yarar |
|---|---|---|
| `--ad` | Kullanıcı | Asistanın sana hitap ettiği ad |
| `--asistan` | Logos | Asistanın adı |
| `--ozel "Günlük"` | `🔒 Özel Alan` | Yapay zekâya kapalı klasör. Birden çok kez verilebilir. |
| `--hafiza` | `🔮 Logos` | Asistanın hafıza klasörü |
| `--proje` | `Projeler` | Proje notlarının klasörü |
| `--zamanla --saat 10:00` | kapalı | Günlük bakım: arama indeksi, sağlık kontrolü, varsa yedek |

Vault'unda zaten bir günlük klasörün varsa onu özel yap: `--ozel "Günlük"`.

---

## Neler kurulur

```
Vault/
├── CLAUDE.md               asistanın kuralları ve hafıza protokolü (Claude Code her sohbette okur)
├── AGENTS.md               aynı protokol, Codex ve diğer ajanlar için
├── 🎯 Hedefler.md           "- [ ] hedef" satırları; açık olanlar her oturumun başında görünür
├── ⚡ Quick Notes.md        hızlı yakalama
├── Projeler/               her proje için bir not: ne, sıradaki adım, öğrenilenler
├── 🔒 Özel Alan/            yapay zekâya kapalı
├── 🔮 Logos/                asistanın hafızası
│   ├── Core.md             seninle ilgili kalıcı çekirdek bilgi
│   ├── Facts.md            tarihli olgular ve kararlar
│   ├── Threads.md          süren işler
│   ├── Last-Session.md     son oturumun özeti ve kalan iş
│   ├── 📌 Kararlar.md       tartılıp verilen kararlar ve yeniden açılma koşulları
│   ├── Journal.md          asistanın kısa notları
│   ├── 📼 Epizotlar.md      biten işlerin kaydı
│   └── Session-Handoffs/   sohbetten sohbete devir kayıtları
└── .claude/
    ├── settings.json       kancalar ve izin kuralları (var olan ayarların korunur, önce yedeği alınır)
    ├── commands/           /recall /baglam /doktor /devir /epizot /proje /hafiza
    └── guros/              sistem kodu
```

Bu yapı mevcut klasörlerinin **yanına** eklenir. Kendi düzenin olduğu gibi kalır.

## Nasıl çalışır

Claude Code beş olayda GurOS'u çağırır:

| Olay | Ne olur |
|---|---|
| Oturum başı | Arama indeksi tazelenir. Hedefler, projeler, süren işler ve son oturum asistana verilir. |
| Her mesaj | Recall ilgili notları bulur ve asistana işaret eder. Uzun oturumda hafızayı güncelleme hatırlatması gelir. |
| Asistan durunca | Belirli sayıda mesaj boyunca hafızaya bir şey yazılmadıysa asistan durdurulup yazması istenir. |
| Bağlam sıkıştırılmadan önce | Ayrıntılar özetlenmeden önce bir hafıza yazımı istenir. |
| Her araç çağrısı | Özel klasöre dokunan çağrılar engellenir. |

Hafıza dört türdür: çalışma (açılış bağlamı), epizodik (epizotlar, devir kayıtları), anlamsal (Core,
Facts, Kararlar) ve prosedürel (komutlar, projelerin "öğrenilenler" bölümü). Ayrıntılar için
[docs/NASIL-CALISIR.md](docs/NASIL-CALISIR.md).

### Claude Code dışındaki ajanlar

Codex, Cursor ve benzerleri `AGENTS.md` dosyasını okur ve aynı kurallara uyar. Bu araçlarda kancalar
çalışmadığı için protokol asistandan şunları ister:

- sohbetin başında `python .claude/guros/baglam.py` çalıştırması,
- aramak için `recall.py` kullanması,
- hafızayı kendisinin yazması.

Bu araçlarda gizlilik koruması asistanın kurallara uymasına dayanır. Kod düzeyinde engel yalnızca
Claude Code'da vardır.

## Gizlilik

- **Özel klasör iki katla korunur.**
  - Birinci kat bir kancadır. Klasörün adını geçiren her okuma, düzenleme ve kabuk komutunu engeller.
    Klasörü ad vermeden süpüren aramaları da engeller: vault kökünden `grep -r`, `find .`, yolsuz Grep,
    `**/*.md` gibi joker desenleri.
  - İkinci kat Claude Code'un izin kurallarıdır: `Read(./🔒 Özel Alan/**)` ve `Edit(...)`.
- **Özel klasör aramaya girmez.** Recall o klasörü hiç indekslemez. Devir ve epizot kayıtları
  klasörün adını içeren metni yazmayı reddeder.
- **Koruma bir emniyet kemeridir, kasa değil.** Kendi dosyaları açan bir betik
  (`python -c "open(...)"`) gibi dolaylı yolları her durumda yakalayamaz. Sınır, kurallara uyan bir
  asistanın kazara içeri girmesini önlemektir. İşletim sistemi düzeyinde engel istiyorsan Claude Code'un
  [sandbox](https://code.claude.com/docs/en/sandboxing) özelliğini aç. Gerçekten hassas
  bilgiyi vault dışında ya da şifreli tut.
- **Arama yereldir, sohbet yerel değildir.** Recall, bağlam ve hafıza betikleri bilgisayarından
  dışarı hiçbir şey göndermez. Ancak asistanın okuduğu her not, sohbetin bir parçası olarak yapay zekâ
  sağlayıcısına (Anthropic, OpenAI…) gider. Asistana göstermek istemediğin şeyi özel klasörde tut.
- **Sırlar notlara girmez.** Parolalar ve API anahtarları bir parola yöneticisinde durmalı.
  İsteğe bağlı yedek, her commit'ten önce anahtar ve token desenlerini tarar. Bir eşleşme bulursa
  commit atmaz.

## Günlük kullanım

Asistanla normal konuş. Gerisini protokol halleder. İşine yarayabilecek komutlar:

| Komut | Ne yapar |
|---|---|
| `/recall bütçe` | Vault'ta ara |
| `/baglam` | Açılış bağlamını yeniden göster |
| `/proje` | Proje notu aç, sıradaki adımı ya da öğrenilen bir dersi ekle |
| `/devir` | Bu sohbetin devir kaydını yaz |
| `/epizot` | Biten bir işi kaydet |
| `/hafiza` | Hafızayı şimdi güncelle |
| `/doktor` | Sağlık kontrolü |

İpuçları:

- Hedeflerini `🎯 Hedefler.md` dosyasına `- [ ] ...` diye yaz. Açık olanlar her sohbetin başında görünür.
- Bir proje başlatınca asistandan proje notu açmasını iste. Bir sonraki sohbette nerede kaldığını bilir.
- Obsidian'ı telefonla eşitliyorsan asistan notları yeniden yazmak yerine sonlarına ekler. Bu,
  eşitleme çakışmalarını önler.

## Güncelleme, yedek, kaldırma

```bash
git pull                                              # indirdiğin klasörde
python kur.py --vault "<vault>" --ad "<ad>" --uygula  # yalnızca sistem kodu ve GurOS bloğu yenilenir
```

- **Yedek** isteğe bağlıdır ve vault'u **özel** bir git deposuna gönderir:
  `python .claude/guros/yedek.py --kur https://github.com/<sen>/<özel-repo>.git`.
  Özel klasör yedeğe girmez.
- **Kaldırma:** `python kur.py --vault "<vault>" --kaldir --uygula`. Kancalar ve sistem kodu silinir.
  Notların ve hafıza klasörün yerinde kalır.

Zamanlama, yedek ve sorun giderme için [docs/BAKIM.md](docs/BAKIM.md).

## Sık sorulanlar

**Var olan vault'uma kurarsam notlarım bozulur mu?**
Hayır. Kurulum yalnız eksik dosyaları ekler.
- `CLAUDE.md` zaten varsa metnine dokunulmaz. Protokol `CLAUDE.guros.md` dosyasına yazılır, senin
  dosyanın sonuna tek bir `@CLAUDE.guros.md` satırı eklenir.
- `.claude/settings.json` değişmeden önce yedeklenir.
- Önce planı görmeden hiçbir şey yazılmaz.

**Ücretli bir şey gerekiyor mu?**
GurOS'un kendisi ücretsizdir. Claude Code ya da Codex kendi abonelik koşullarıyla çalışır.

**İnternet gerekiyor mu?**
Arama ve hafıza betikleri için gerekmez. Yapay zekâ asistanının kendisi için gerekir.

**Asistanın adını değiştirebilir miyim?**
Evet. Kurarken `--asistan "Ada"` ver ya da `.claude/guros/ayarlar.json` dosyasını düzenleyip
`kur.py`'yi yeniden çalıştır.

**Obsidian'da bir eklenti gerekiyor mu?**
Hayır. Her şey düz Markdown'dır.

**Testler?**
`python tests/run_tests.py`. Testler geçici bir vault kurar. Gerçek vault'una dokunmaz.

## Bu pakette olmayanlar

Videoda görünen bazı parçalar kişisel kurulumuma özeldir ve bu pakete alınmadı: kişisel otomasyonlarım
ve tabii ki notlarım. Bu paket, herkesin kendi vault'unda kullanabileceği çekirdektir: hafıza, bağlam,
arama, gizlilik ve bakım.

## Lisans

[MIT](LICENSE). İstediğin gibi kullan, değiştir, paylaş.

---

<sub>**English:** GurOS adds persistent memory, automatic session context, local Turkish/English
keyword search and a privacy guard to an Obsidian vault, for Claude Code (full) and Codex/other agents
(via `AGENTS.md`). Give this URL to an AI coding agent and say "install this for me", or run
`python kur.py --vault <path> --ad <name>` (plan) and then add `--uygula` (apply). Standard-library
Python only. The prompts and notes are in Turkish.</sub>
