# Turn the Page 0.42

Beş bölümlük, elde çizilmiş defter aksiyon oyunu. Bu sürüm boss çizimine korumalı kamera girişi, iki fazlı mini bosslar, değişen düşman dalgaları, yeni silah davranışları ve oynanabilir final sonrası sayfa ekler.

Türkçe, English, Deutsch ve Italiano desteklenir. Dil ana menüden veya Ayarlar'dan değişir. Eski kampanya kayıtları kullanılabilir; yeni bosslar ana ilerleyişi zorunlu olarak durdurmaz.

0.42 cilası: menülerde fare ve klavye aynı anda iki satırı seçmez; kontrolcüyle seçim ve geri tuşları doğru gösterilir. Ressam yeni menzilli silahlara uygun tamamlayıcı araç önerir. Otomatik hediye çizimi E etkileşimine veya yeni çatışmaya tuvali bırakır; yarım kalan ödül sonraki sakin aralıkta yeniden çizilir.

## Savaş ve final sonrası

Her bossun gerçek çizimi 3,2 saniyelik yakın kamera girişinde oluşur; çizim bitmeden saldırılar başlamaz. Dört yeni mini boss 10 can, bulut bossu 8 can ve ikinci fazda iki uyarılı saldırı kullanır. Normal dalgalar 2–5 düşman ve farklı birlik düzenleri içerir.

Katlama Arbaleti çarpınca üç parçaya ayrılır; Yörünge Testeresi durduğu yerde iki kez keser. Beş bölümde başlangıç silahından sonra üç farklı seçim çizilir. Q ile elindekiler arasında geçebilirsin.

Finalden sonra Son Söz’de üç hatıra çizdirip defteri imzalarsın. Tamamlanan kayıtlarda ana menüdeki Sayfaları Yeniden Oyna seçeneği beş bölümü ve kapanışı açar. Öğrenilen eskizler korunur.

## Yeni mini bosslar

- Kovboy: Pirinç Çalı — yuvarlanma, kement ve mahmuz saldırıları. Kalıcı atılma dolum avantajı.
- Uzay: Yörünge Yengeci — yörünge atışları, kıskaç ve krater saldırıları. Kalıcı mermi ömrü avantajı.
- Ajan: Karbon Tazısı — hamle, damga ve kopya atışları. Kalıcı tabanca doldurma avantajı.
- Final: Taslak Güvesi — sayfa kesileri, mürekkep tozu ve kanat saldırıları. Kalıcı bıçak bitiriş erişimi.

Bulut bossu ve üç eski gizli cep korunur. Yeni rotalarda önce Ressamın geçidi çizilir, sonra karşılaşmayı E ile seçersin. Yenilmiş boss yeniden doğmaz; alınmamış rün yeniden yüklemede bekler. Toplam 19 kalıcı eskiz rünü vardır.

## Müzik

12 bossun her birinde farklı lisanslı kayıt çalar. Japon sayfasında şamisen/taiko ve senfonik rock; western'de gitar ve ağır orkestralı ritim; uzayda koro, synth ve orkestralı aksiyon; ajanda endüstriyel/noir müzik; finalde gotik org ve orkestralı müzik kullanılır. Kayıtlar daha hafif pasajlardan seçilmiş 27–38 saniyelik stereo döngülerdir; girişte ses yumuşakça yükselir. Boss sırasında bölüm müziği kapanır; saldırı uyarıları korunur. Ana menüde C ile açılan künye üç sayfadır; oklar, tıklama veya kontrolcüyle gezilir.

Eserler ve kaynak/lisans bilgileri: [Boss künyesi](assets/audio/boss/CREDITS.md), [tüm ses kaynakları](assets/audio/THIRD_PARTY.md). Boss kayıtları CC BY 4.0 kapsamındadır. Bölüm müzikleri ve defter efektleri korunur.

## Oynama ve doğrulama

A/D veya ←/→: hareket; Space/W/↑: zıplama; F/J veya sol tık: saldırı; Shift/K veya sağ tık: atılma; E: etkileşim; R: doldurma; Q/fare tekeri: silah. Eğitim en az 75 saniye sürer.

Python 3.13 ve pygame 2.5+ ile:

```sh
python3 -m pip install -r requirements.txt
python3 main.py
python3 -m unittest discover -s tests
python3 tools/build_release.py
```

Paket üretmek için PyInstaller gerekir. Oyun ve kaynak paketi ses dönüştürme aracı gerektirmez; hazır OGG kayıtları assets klasöründe bulunur. Native doğrulama oyunu SDL dummy sürücüleriyle açar; eğitim, beş bölüm geçişi, 12 boss sesi, beş mini boss, korumalı kamera girişi, oynanabilir kapanış ve dört dili kontrol eder.
