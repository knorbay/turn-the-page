## Beta r8 — Hareket ve dövüş okunabilirliği

- Koşuda yere basan ayaklar, eklemli sıçrama/iniş pozları, kısa kalem dash izleri ve sayfaya özel vuruş duruşları.
- Çizerin kalemi yeniden çizilen karakterin gerçek diz ve ayak çizgilerini takip eder.
- Bowie zincirinin hedefte kalan kesikleri ve Field Knife bitiriş fırsatı görünür. Yarım kalmış eski kombolar tam zincir bonusu vermez.
- Sekmiş atışlar zırhı gerçekten geldikleri yönden sınar; engellenen vuruşlar başarılı kesik efekti üretmez.
- Final bossun yönü ve yörünge bossunun atış çizgileri uyarıdan sonra değişmez. Açıklık işaretleri kalan vuruş hakkıyla birlikte kapanır.
- Düşmanlar yeni saldırı uyarılarını aralıklı başlatır; yakındaki mermiler ve silinen zemin de hesaba katılır. Başlamış saldırı ve takip hareketi durdurulmaz.
- Menü ve indirilen dosyalar r8 sürümünü gösterir. Mevcut kayıtlar uyumludur.
- 160 otomatik kontrol; gerçek oyun çizimleriyle altı bossun açık/kapalı hâlleri ve beş sayfanın hareket pozları incelendi.

## Önceki combat cilası

- Üç yeni düşman: kilitli mürekkep sütunu, üçlü alçak iğne yaylımı ve hücumdan sonra kıvılcım izi.
- Beş sayfanın başlangıç yakın dövüş silahı ayrı kombolara ve özel etkilere sahip.
- Altı gerçek boss yeni fazlar ve okunabilir karşı hamleler kazandı; Baby Face sekansı korundu.
- Silah sesleri, düşman uyarıları ve boss faz/açıklık sesleri çeşitlendirildi.
- 138 test geçti; beş sayfalık otomatik rota tamamlandı. İnsan oyuncuyla zorluk ve his testi hâlâ gerekli.

# TURN THE PAGE — Beta 0.9.0

Bu sürümün odağı bölüm kimliği, silah hissi, anlamlı sketchler ve güvenilir dövüş akışı. Beş sayfa, 23 zorunlu karşılaşma, 20 normal düşman türü, altı ana boss ve dev bebek sahnesi var.

## Can

Can üst sınırı üç. Her yeni arenaya tam canla girilir; ön dalgadan sonra ana boss geldiğinde de üç can yenilenir. Aynı arenanın normal dalgaları veya bossun fazları can doldurmaz. Dövüş sonundaki +1, boss girişindeki +2 ve Çizerin arada verdiği +1 kaldırıldı. Üç kalp dövüşler arasında da görünür. Boş kalp kırık çizilir; hasarda ve yenilenmede ayrı tepki verir.

## Bölümün silahı

| Sayfa | Araçlar ve oynanış farkı |
| --- | --- |
| Ronin | Ink Katana: uzun erişim, ters ikinci kesiş, ağır üçüncü vuruş. |
| Batı | Bowie Knife; altı mermili, belirgin ritimli Six-Shooter; art arda iki güçlü ve geniş atış yapan Double Barrel. |
| Uzay | Ion Edge; düz uçan, üç kez seken Orbit Pulse; düşman atışlarını daha geniş alanda silebilen Null Cannon. |
| Ajan | Kısa ve hızlı Field Knife; daha seri, hassas Suppressed Pistol; dar dağılımlı Breach Shotgun. |
| Son Taslak | Kurşun kalem, lastik, silgi ve keçeli kalem silahları defter araçlarına geri döner. |

Silahın yerdeki, eldeki ve envanterdeki çizimi aynı kimliği taşır. Envanter yalnızca toplanan ve o sayfaya ait silahlarla büyür. Ekrandaki 1–6 kutuları kaldırıldı; Q veya tekerlek edinilen silahlar arasında dolaşır. Mermi ve dolum durumu görünür. Çizilen bir silah yakından alınır. Ağır bitiricinin toparlanması artık yanlışlıkla genel saldırı süresiyle kesilmez.

## Sketchlerin anlamı

On iki çizimin her biri kalıcı bir teknik öğretir. Kenardan ayrıldıktan sonra daha geç zıplama, havada daha çabuk yön değiştirme, üçüncü kılıç darbesinin uzaması, kısa dash beklemesi, tabanca dolumu/hızı/delmesi, tüfek dağılımı/itmesi, sekmeli atışlar ve silgi dolumu bunlar arasında.

Etkisi çizimi almadan önce görünür. Back Pages kazanılmış teknikleri ve ilgili silahın bu sayfada kullanılabilir olup olmadığını açıklar. Eski kayıtta toplanmış sketchler de etkilerini alır. Ölüm ve bölüm tekrarı bonusları üst üste eklemez. Sketchler can sınırını yükseltmez.

## Çizer ve bölüm akışı

Batı bölümünde çatışmanın içinde tetiklenen kenar geçişi düzeltildi. Yol sahneleri arena bitene kadar bekler. İlk arena platformu düşmanlar başlamadan çizilir; sonraki ekleme, silme ve katlama hamleleri dalgalar arasındaki boşlukta yapılır. Çizer aynı anda iki düzenleme başlatmaz. Oyuncunun bastığı veya inmekte olduğu platform korunur.

Final bossun canlı müdahalesi devam eder; saldırının üzerine büyük bir el bindirmek yerine küçük kalem uçları ve taslak işaretleri kullanır. Beş sayfanın platform çizgileri de malzemelerine göre ayrılır.

## Dil, ses ve bosslar

Yirmi ders notu İngilizceye çevrildi; oyun içi dil İngilizce. Dil seçeneği eklenmedi. Sayfa geçişindeki okul zili ve müziğin altındaki çok hafif sınıf mırıltısı korunur. Sınıf katmanı sözcüksüz sentezdir.

Moon Compass, Wanted Sketch, Railroad Stapler, Orbital Mistake, Head of Redaction ve Final Editor kendi saldırı kurallarını korur. Dev bebekteki iki kasıtlı yenilgi, yeniden çizilme, bıyık, “It's more fair now.” ve Excalibur ile dönüş korunmuştur.

## Açma

Normal oyun için `run_paper_story.command`. Bir sayfayı denemek için `bolum_testi.command`; altı ana bossu doğrudan denemek için `bosslari_dene.command`. Deneme modları ana kaydı değiştirmez. Python 3.10+ ve Pygame gerekir.

Önceki oyuna devam etmek için önceki klasördeki `paper_story_save.json` dosyası yeni oyun klasörüne kopyalanabilir. Bu pakette oyuncu kaydı bulunmaz.

## Kontroller

Hareket A/D veya oklar; zıplama Space; saldırı F/J veya sol tık; dash Shift/K veya sağ tık; dolum R; silah değiştirme Q veya tekerlek; sketch inceleme E; duraklatma Esc. Kol desteği devam eder.

111 test geçti. Otomatik kontroller gerçek hasar, mermi çarpışması, üç can akışı, kayıt yükleme, sketch etkileri, çizim zamanlaması ve beş bölümün ilerleyişini kapsar. Yeni oyundan finale kadar denemede yalnızca dev bebek sahnesindeki iki kasıtlı ölüm gerçekleşti. Görseller oyun motorunun gerçek çizimlerinden alınmıştır. Gerçek oyuncularla ilk oynanış zorluğu ve süre testi hâlâ gereklidir.
