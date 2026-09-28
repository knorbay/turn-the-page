# Turn the Page — 0.12.0 Karbon Revizyonu

Bu sürüm 0.11.2 görüntü düzeltmesinin üzerine gelir. Dünya yine doğrudan opak
kağıt yüzeyine çizilir; siyah sahne sorununa neden olan ara katman geri eklenmedi.

## Oynanış ve içerik

- Ajan sayfasındaki dev makas yeniden tasarlandı: karalanmış paltosu, sansürlü
  yüzü, evrak çantası ve copuyla Redaksiyon Müdürü. Üç fazın son ikisinde önce
  çizilen ateş hatları ardından gerçek, dash ile geri çevrilebilir mermiler var.
  Alçak süpürmeyi zıplayarak aş; zemini silen damgadan ve kırmızı X'ten uzaklaş;
  açık çekirdeği vur. Açılışta başıboş mermiler temizlenir.
- İki yeni silah: **Karbon Tüfek**, bir atıştan sonra 1,8 saniye doldurulur,
  birden fazla hedefi azalan hasarla deler ve geri teper. **Dönen Kat**, tek bir
  katlanmış yıldız fırlatır; geri dönerken oyuncuya yönelir ve dönüşte yeniden
  isabet edebilir. Aynı anda yalnızca bir yıldız bulunabilir.
- Dönen Kat, ilk sayfanın `practice_monster` çizim mücadelesinden kazanılır;
  ajan sayfasında çatılar ile ofis arasındaki 6520 konumunda da çizilir.
  Karbon Tüfek ajan arşivi (`agent_badge`) mücadelesinin ödülüdür. Son sayfanın
  `last_homework` mücadelesi de Dönen Kat'ı verir. Q / tekerlek ile değiştirilir.
- 12 kayıp çizim artık E ile başlatılan, ana rotayı kilitlemeyen yan
  mücadelelere bağlıdır. İlk çizimde bir, diğerlerinde birbirinden farklı iki
  rakip turu vardır. Çizer düşmanı önce çizer; tamamlanmamış düşman vurulamaz ve
  saldıramaz. Mücadele bitince çizimi almak için tekrar yanına dönüp E kullanılır.
  Uzaklaşmak mücadeleyi sıfırlar. Eski kayıtta toplanmış çizimler korunur.
- Çizer her sayfanın yan mücadelelerini kendi temasıyla açar, ikinci turda
  uyarır ve çizim alındığında cevap verir. Kahraman bu elleri de bakışıyla takip eder.
- Arka planlar artık ortak yüz/uçak döngüsünü kullanmaz. Tapınak, bambu,
  fenerler, ay kapısı; aranan posteri, tren, su kulesi, salon; yörünge,
  roket, teleskop, enkaz; dosya dolabı, sansürlü belge, ofis planı ve kamera
  çizimleri sayfa boyunca farklı başlıklarla yerleşir. Son sayfada reddedilmiş
  kahraman taslakları bulunur. Ajan, haydut ve yıldız gözcüsü de yeniden çizildi.

## Doğrulama

191 otomatik test geçti: mevcut kampanya rotası, boss açıklıkları, silah
çarpışmaları, kayıtlar, görüntü görünürlüğü ve yeni yan mücadele/silah sözleşmeleri.
Son yerleşim düzeltmesinden sonra 8 yeni içerik testi yeniden geçti.
Yeni çizimler oyun renderer'ından alınan beş sayfalık önizlemede incelendi.
Paketlenmiş 0.12.0 macOS uygulaması gerçek pencerede açıldı; Continue ile
oyuna girilerek yeni defter karalamaları, karakter ve çizer konuşması görüldü.

Bu sürüm mevcut tüm bossları veya tüm düşmanları baştan çizmez. Ana boss
revizyonu ajan sayfasındadır; diğer bossların çalışan mekanikleri korunmuştur.
