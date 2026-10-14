---
title: Başlarken
type: rehber
tags: [guros]
---

# 👋 Hoş geldin, {AD}

Bu vault artık bir ikinci beyin. {ASISTAN} notlarını okuyabilen, seni hatırlayan ve her sohbete kaldığın yerden
başlayan yapay zekâ ortağın. Bu not nasıl kullanacağını anlatır; okuyunca silebilirsin, sistem ona ihtiyaç duymaz.

## İlk sohbet

1. Bu klasörde bir terminal aç ve Claude Code'u başlat: `claude`
2. İlk açılışta **"Do you trust the files in this folder?"** sorusuna **Yes** de. Hafıza ve gizlilik koruması
   ancak o zaman devreye girer.
3. **merhaba** yaz. {ASISTAN} kendini tanıtır ve seni tanımak için birkaç soru sorar. Cevapların hafızasına yazılır.

Codex kullanıyorsan aynı klasörde `codex` başlat; kuralları `AGENTS.md` dosyasından okur.

## {ASISTAN_YE} neler diyebilirsin

- "Bugün neye odaklanmalıyım?"
- "Yeni bir proje başlatıyorum: kişisel web sitem. Takibe al."
- "Şunu hatırla: sabahları daha verimli çalışıyorum."
- "Geçen hafta bütçe konusunda ne karar vermiştik?"
- "Bu sohbeti kaydet, yarın kaldığımız yerden devam edelim."

## Ne nerede

| Yer | Ne işe yarar |
|---|---|
| [[🎯 Hedefler]] | `- [ ] hedef` satırların. Açık olanları {ASISTAN} her sohbetin başında görür. |
| [[⚡ Quick Notes]] | Aklına geleni hızlıca yaz: `- YYYY-AA-GG: not` |
| `{PROJE}/` | Her proje için bir not: ne, sıradaki adım, öğrenilenler. |
| `{HAFIZA}/` | {ASISTAN_NIN} hafızası. Okuyabilir, yanlışı düzeltebilirsin. |
| `{OZEL_KOK}` | Yapay zekâya kapalı. Günlük gibi şeyler buraya. |
| `CLAUDE.md`, `AGENTS.md` | {ASISTAN_NIN} kuralları. Kendi kuralını GurOS bloğunun dışına ekleyebilirsin. |

## Gizlilik

{OZEL_LISTE} klasörlerine {ASISTAN} giremez: okumaz, aramaz, değiştirmez; bu klasörler yedeğe de girmez.
Arama (Recall) ve hafıza betikleri bilgisayarından dışarı bir şey göndermez. {ASISTAN_NIN} sohbette okuduğu notlar
ise sohbetin parçası olarak yapay zekâ sağlayıcısına gider; göstermek istemediğin şeyi özel klasörde tut.

## Komutlar

`/recall` vault'ta ara · `/baglam` açılış bağlamı · `/proje` projeler · `/devir` sohbeti kaydet ·
`/epizot` biten işi kaydet · `/hafiza` hafızayı gözden geçir · `/doktor` sağlık kontrolü
