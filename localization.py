"""Four runtime languages, independent of gameplay and saved identifiers."""
from __future__ import annotations
import re

_language = 'tr'
SUPPORTED_LANGUAGES = ('tr', 'en', 'de', 'it')
LANGUAGE_NAMES = {'tr': 'Türkçe', 'en': 'English', 'de': 'Deutsch', 'it': 'Italiano'}

def normalize_language(language):
    return language if isinstance(language, str) and language in SUPPORTED_LANGUAGES else 'tr'

def set_language(language):
    global _language
    _language = normalize_language(language)

def get_language():
    return _language

TR = {
'TRAINING':'EĞİTİMİ OYNA',
'FIELD NOTES / 0.31':'SAHA NOTLARI / 0.31',
'TRAINING COMPLETE / your campaign progress is kept':'EĞİTİM TAMAMLANDI / kampanya kaydın korundu',
'F / J or left click: destroy all four targets along the practice lane.':'F / J ya da sol tık: alıştırma yolundaki dört hedefi yok et.',
'Shift / K or right click: leave the frozen red column before it fires. Dodge three warnings.':'Shift / K ya da sağ tık: kırmızı sütundan atış gelmeden çık. Üç uyarıyı atılmayla aş.',
'E at the pencil lever: ask the Artist for stairs. Climb to the rune seal and read it with E.':'Kalem kolunda E: Ressam merdiven çizsin. Rün mührüne tırman ve E ile oku.',
'TRAINING YARD / FOUR TARGETS':'EĞİTİM ALANI / DÖRT HEDEF',
'DODGE LANE / FOLLOW THE WARNING':'KAÇIŞ PARKURU / UYARIYI İZLE',
"THE ARTIST'S STAIRS / CLIMB TO THE RUNE":'RESSAMIN MERDİVENİ / RÜNE TIRMAN',
'E / ARTIST':'E / RESSAM',
'E / ask the Artist to draw the training stairs':'E / Ressamdan eğitim merdivenini çizmesini iste',
'Good dodge. The red mark stayed where it was drawn.':'Güzel kaçış. Kırmızı iz çizildiği yerde kaldı.',
'Practice only: dash out of the red column after it appears.':'Alıştırma: kırmızı sütun belirince dışarı atıl.',
'EXPLORE / three blue marks above the road':'KEŞFET / yolun üstünde üç mavi işaret',
'E / trace the blue waypoint':'E / mavi rota işaretini çiz',
'E / THREE BLUE MARKS / +1 HEART':'E / ÜÇ MAVİ İŞARET / +1 KALP',
'The Artist traced your route and restored one heart.':'Ressam rotanı çizdi ve bir kalbini yeniledi.',
'BAMBOO WALK':'BAMBU GEÇİDİ','THE OLD VIADUCT':'ESKİ VİYADÜK','SATELLITE WALK':'UYDU GEÇİDİ',
'THE ROOFTOP ARCHIVE':'ÇATI ARŞİVİ','THE UNWRITTEN GARDEN':'YAZILMAMIŞ BAHÇE',
'HIGH THRUST — STAY LOW':'YÜKSEK SAPLAMA — ALÇAKTA KAL',
'LOW RICOCHET — JUMP OR RETURN':'ALÇAK SEKME — ZIPLA YA DA GERİ YANSIT',
'LOW THEN HIGH — JUMP, THEN LAND':'ALÇAK SONRA YÜKSEK — ZIPLA, SONRA İN',
'COMET RAIN — KEEP THE BLUE GAP':'KUYRUKLU YAĞMURU — MAVİ BOŞLUKTA KAL',
'JUMP THE CLOSING BRACKET':'KAPANAN AYRACIN ÜZERİNDEN ZIPLA',
'ERASER RAIN — LEAVE THE NUMBERED MARKS':'SİLGİ YAĞMURU — NUMARALI İZLERDEN ÇIK',
'The Artist:':'Ressam:', 'the Artist:':'Ressam:',
'NEW GAME':'YENİ OYUN','CONTINUE':'DEVAM ET','SETTINGS':'AYARLAR','QUIT':'ÇIKIŞ',
'BACK PAGES':'ESKİZ DEFTERİ','ACHIEVEMENTS':'BAŞARIMLAR','ACHIEVEMENT':'BAŞARIM',
'RESTART PAGE':'SAYFAYI BAŞLAT','TITLE':'ANA MENÜ','CONTROLS':'KONTROLLER','Back':'Geri',
'Master volume':'Ana ses','SFX volume':'Efekt sesi','Music volume':'Müzik sesi',
'Window size':'Pencere boyutu','Fullscreen':'Tam ekran','Language':'Dil','YES':'EVET','NO':'HAYIR',
'page held open':'sayfa açık tutuldu','Every line leaves a mark.':'Her çizgi bir iz bırakır.',
'FIELD NOTES / 0.30':'SAHA NOTLARI / 0.30','A longer lesson. Hidden margins.':'Uzun eğitim. Gizli kenarlar.',
'New attacks. Ideas worth keeping.':'Yeni saldırılar. Saklanacak fikirler.',
'Arrows / W S select  ·  ENTER play  ·  click to choose':'Oklar / W S: seç  ·  ENTER: başlat  ·  tıkla: seç',
'ESC continue  ·  arrows select  ·  ENTER confirm':'ESC: devam  ·  oklar: seç  ·  ENTER: onayla',
'Learn the line, then make it yours.':'Çizgiyi öğren, kendi yolunu çiz.',
'Move':'Hareket','Jump':'Zıplama','Attack':'Saldırı','Dash / return':'Dash / geri yansıtma',
'Interact / sketch':'Etkileşim / eskiz','Reload / switch':'Doldur / değiştir','Drop through':'Platformdan in',
'Pause / fullscreen':'Duraklat / tam ekran',
'Space / W / Up  ·  release for a short jump':'Space / W / ↑  ·  kısa zıplamak için bırak',
'F / J  ·  left click aims at the pointer':'F / J  ·  sol tık: imlece nişan al',
'Shift / K  ·  right click':'Shift / K  ·  sağ tık','R  /  Q or mouse wheel':'R  /  Q ya da fare tekeri',
'S or Down + any jump key':'S ya da ↓ + zıplama tuşu','ENTER / ESC   Back':'ENTER / ESC   Geri',
'Rejected drawings. Real techniques. Learned ideas survive every redraw.':'Atılmış çizimler. Kalıcı teknikler. Öğrendiğin fikirler yeniden çizilince de kalır.',
'next  >':'sonraki  >','<  previous':'<  önceki','A / ESC   close':'A / ESC   kapat',
'B / ESC   close the back cover':'B / ESC   defteri kapat','PAD-A / PAD-B   close the back cover':'PAD-A / PAD-B   defteri kapat',
'PAD-A / PAD-B   close':'PAD-A / PAD-B   kapat',
'D-PAD choose   •   PAD-A confirm   •   PAD-B continue':'D-PAD: seç   •   PAD-A: onayla   •   PAD-B: devam',
'D-PAD change  •  PAD-A confirm  •  PAD-B returns':'D-PAD: değiştir  •  PAD-A: onayla  •  PAD-B: geri',
'click or use arrows  •  F11 fullscreen  •  ESC returns':'Tıkla ya da okları kullan  •  F11: tam ekran  •  ESC: geri',
'CONTROLLER CONNECTED':'KONTROLCÜ BAĞLI','CONTROLLER READY':'KONTROLCÜ HAZIR',
'condition not written down':'koşul henüz yazılmadı','the page remains open   —   ENTER':'sayfa açık kalır   —   ENTER',
'checkpoint — redrawn here':'kayıt noktası — burada yeniden çizilirsin','dash':'dash','IN HAND':'ELİNDEKİ SİLAH',
'RELOAD':'DOLDUR','EMPTY HANDS':'BOŞ ELLER','the next tool is still being drawn':'sonraki silah henüz çiziliyor',
'INK KATANA':'MÜREKKEP KATANA','PENCIL BLADE':'KALEM BIÇAĞI','INK PISTOL':'MÜREKKEP TABANCASI',
'RETURNING FOLD':'GERİ DÖNEN KATLAMA','OVERSIZED PENCIL':'DEV KALEM','SIX-SHOOTER':'ALTIPATLAR',
'DOUBLE BARREL':'ÇİFTE','CHALK CAPSULE':'TEBEŞİR KAPSÜLÜ','METEOR CHALK':'METEOR TEBEŞİRİ',
'CARBON RIFLE':'KARBON TÜFEĞİ','MARKER SHOTGUN':'KEÇELİ POMPALI','ERASER CANNON':'SİLGİ TOPU',
'NULL CANNON':'BOŞLUK TOPU','RUBBER BAND':'LASTİK SAPAN','ORBIT PULSE':'YÖRÜNGE DARBESİ',
'BOWIE KNIFE':'BOWIE BIÇAĞI','ION EDGE':'İYON KESKİNİ','SUPPRESSED PISTOL':'SUSTURUCULU TABANCA',
'BREACH SHOTGUN':'YARMA POMPALISI','THE VERY DRAMATIC SWORD':'AŞIRI DRAMATİK KILIÇ',
'KING ARTHUR · subtlety unavailable':'KRAL ARTHUR · incelik bulunamadı',
'draw dash · return step · rising launch':'atılma kesişi · geri adım · yükselen vuruş',
'one fold at a time · catch the return line':'tek katlama · dönüş çizgisini yakala',
'wind up · crush · erase shots in reach':'hazırlan · ez · yakındaki mermileri sil',
'six heavy shots · deliberate rhythm':'altı güçlü atış · kararlı ritim',
'arc over cover · two gentle bursts':'siper üstünden yay çiz · iki patlama',
'two quick blasts · wide spread':'iki hızlı atış · geniş saçılım',
'arc around shields · small impact cloud':'kalkan etrafından yay · darbe bulutu',
'three ricochets · bank off ink':'üç sekme · mürekkepten sektir',
'cut through volleys · straight flight':'yaylımı del · düz uçuş',
'one round · pierces a line · long reload':'tek mermi · hattı del · uzun doldurma',
'close-range ink burst':'yakın mesafe mürekkep patlaması','erase incoming fire':'gelen atışı sil',
'steady ink fire':'düzenli mürekkep atışı','three strokes · heavy finish':'üç vuruş · güçlü bitiriş',
'01 / FIND YOUR FEET':'01 / AYAKTA DUR','02 / FOLLOW THE INK':'02 / MÜREKKEBİ İZLE',
'03 / THE RETURNING FOLD':'03 / GERİ DÖNEN KATLAMA','04 / LEAVE THE RED LINE':'04 / KIRMIZI ÇİZGİDEN KAÇ',
'05 / IDEAS THAT STAY':'05 / KALICI FİKİRLER',
'A / D or Left / Right: move. Explore the first lines.':'A / D ya da ← / →: hareket et. İlk çizgileri keşfet.',
'Space / W / Up: jump. Release early for a short jump. Collect the drawn tool.':'Space / W / ↑: zıpla. Kısa zıplama için erken bırak. Çizilen silahı al.',
'F / J or left click: hit the practice drawing with your Returning Fold.':'F / J ya da sol tık: Geri Dönen Katlama ile alıştırma hedefini vur.',
'Shift / K or right click: dash three times. Watch the recovery line.':'Shift / K ya da sağ tık: üç kez atıl. Dolum çizgisini izle.',
'E at the lesson seal: read how sketches work. B in pause opens your learned runes.':'Eğitim mühründe E: eskizleri öğren. Duraklatınca B: öğrendiğin rünler.',
'Destroy the practice drawing':'Alıştırma hedefini yok et','Seal read':'Mühür okundu','Read the seal with E':'E ile mührü oku',
'E / LESSON SEAL':'E / EĞİTİM MÜHRÜ',
'E  read the lesson seal / sketches are lasting runes':'E  eğitim mührünü oku / eskizler kalıcı rünlerdir',
'SKETCH RUNES: Permanent techniques, clear numeric effects. They survive page turns and redraws. Find them on optional routes.':'ESKİZ RÜNLERİ: Kalıcı teknikler ve net sayısal etkiler. Sayfa çevrilince ve yeniden çizilince korunur. Gizli rotalarda bulabilirsin.',
'FIRST LESSON COMPLETE / the combat page is open':'İLK EĞİTİM TAMAMLANDI / savaş sayfası açıldı',
'Lost Sketches are discarded ideas. Keep them to learn lasting tricks across pages.':'Kayıp Eskizler atılmış fikirlerdir. Sayfalar boyunca kalıcı teknikler öğrenmek için onları sakla.',
'LOST SKETCH — clipped into the back pages.':'KAYIP ESKİZ — deftere eklendi.',
'UNDISCOVERED SKETCH':'BULUNMAMIŞ ESKİZ','ACTIVE':'ETKİN','NEEDS ITS WEAPON':'SİLAH GEREKLİ','SAVED / NEEDS ITS WEAPON':'SİLAH GEREKLİ',
'A rejected drawing. A useful idea.':'Atılmış bir çizim. Yararlı bir fikir.','Clipped into BACK PAGES':'ESKİZ DEFTERİNE eklendi',
'SEALED / finish the margin challenge':'MÜHÜRLÜ / kenar sınavını tamamla','E  keep this drawing':'E  bu çizimi sakla',
'E  examine lost sketch':'E  kayıp eskizi incele','Defeat the rejected drawing below':'Aşağıdaki reddedilmiş çizimi yen',
'E  challenge the drawing / optional':'E  çizime meydan oku / isteğe bağlı',
'THE FIRST FIGURE':'İLK FİGÜR','SECOND THOUGHT':'İKİNCİ DÜŞÜNCE','PRACTICE MONSTER':'ALIŞTIRMA CANAVARI',
'FOLLOW THROUGH':'VURUŞU TAMAMLA','THE KITE RONIN':'UÇURTMA RONİN','PAPER KITE':'KAĞIT UÇURTMA',
'THE MARGIN HOUSE':'KENAR EVİ','QUICK DRAW':'HIZLI ÇEKİŞ','COFFEE UMBRELLA':'KAHVE ŞEMSİYESİ','TIGHT FOLD':'SIKI KATLAMA',
'THE VICTORY POSE':'ZAFER POZU','MAKE SOME ROOM':'YER AÇ','THE UNUSED TICKET':'KULLANILMAYAN BİLET','THROUGH TICKET':'GEÇİŞ BİLETİ',
'THE APOLOGETIC BEAST':'ÖZÜR DİLEYEN CANAVAR','ELASTIC MEMORY':'ESNEK HAFIZA','THE ERASER SURVIVOR':'SİLGİDEN KURTULAN',
'CLEAN SLATE':'TEMİZ SAYFA','THE SECOND MOON':'İKİNCİ AY','LOW ORBIT':'ALÇAK YÖRÜNGE','THE FORGED BADGE':'SAHTE ROZET',
'FAST INK':'HIZLI MÜREKKEP','THE LAST HOMEWORK':'SON ÖDEV','REVISION RHYTHM':'DÜZELTME RİTMİ',
'THE RONIN':'RONİN','HIGH NOON':'ÖĞLE VAKTİ','THE AGENT':'AJAN','THE LAST DRAFT':'SON TASLAK',
'Jump a little later after leaving an edge.':'Kenardan ayrıldıktan biraz sonra da zıplayabilirsin.',
'Your blade finisher reaches farther.':'Bıçak bitirişin daha uzağa erişir.',
'Change direction faster in the air.':'Havada daha hızlı yön değiştir.',
'Reload your sidearm faster.':'Tabancanı daha hızlı doldur.',
'Your scattergun keeps a tighter spread.':'Pompalı saçılımın daha dar olur.',
'Scattergun hits push enemies farther.':'Pompalı vuruşları düşmanı daha uzağa iter.',
'Sidearm shots pass through one enemy.':'Tabanca atışları bir düşmanın içinden geçer.',
'Ricochet shots bounce one more time.':'Sekmeli atışlar bir kez daha seker.',
'Reload your heavy cannon faster.':'Ağır topunu daha hızlı doldur.',
'Ricochet shots stay in flight longer.':'Sekmeli atışlar daha uzun süre uçar.',
'Sidearm bullets reach their target faster.':'Tabanca mermileri hedefe daha hızlı ulaşır.',
'Your dash becomes ready sooner.':'Atılma daha erken hazır olur.',
'PAGE I':'SAYFA I','PAGE II':'SAYFA II','PAGE III':'SAYFA III','PAGE IV':'SAYFA IV','PAGE V':'SAYFA V',
'Ink of the Ronin':'Roninin Mürekkebi','Dust & Bad Decisions':'Toz ve Kötü Kararlar','A Very Wrong Future':'Çok Yanlış Bir Gelecek',
'The Carbon Agent':'Karbon Ajan','The Last Draft':'Son Taslak',
'THE ARTIST':'RESSAM','ARTIST':'RESSAM',
'WAIT / the Artist is finishing this line':'BEKLE / Ressam çizgiyi tamamlıyor',
'E  trace the first graphite mark':'E  ilk grafit işaretini çiz','E  connect the upper mark':'E  üstteki işareti birleştir',
'E  cross out the red margin':'E  kırmızı kenarı sil','FIRST / lower pencil mark':'İLK / alttaki kalem işareti',
'NEXT / upper pencil mark':'SONRA / üstteki kalem işareti','LAST / cross out the margin':'SON / kenarı sil',
'1 / TRACE':'1 / ÇİZ','2 / CONNECT ABOVE':'2 / ÜSTTE BİRLEŞTİR','3 / CROSS OUT':'3 / SİL',
'THE ARTIST: A step belongs above this line.':'RESSAM: Bu çizginin üstüne bir basamak gerek.',
'THE ARTIST: Yes. Find the last crossed-out mark.':'RESSAM: Evet. Son silinmiş işareti bul.',
'THE ARTIST: Erasing the margin now.':'RESSAM: Şimdi kenarı siliyorum.',
'THE ARTIST: Better. That line can go.':'RESSAM: Daha iyi. Bu çizgi gidebilir.',
'arena sealed — clear every red mark':'arena kapandı — tüm kırmızı izleri temizle',
'arena clear — ink dries, the margin opens':'arena temiz — mürekkep kurur, kenar açılır',
'the gate shuts — a named drawing waits below':'kapı kapanıyor — özel bir çizim aşağıda bekliyor',
'READ THE RED MARK — MOVE, THEN PUNISH':'KIRMIZI İZİ OKU — KAÇ, SONRA VUR',
'Too heavy? You asked for it. Q swaps back.':'Ağır mı? Sen istedin. Q ile geri değiştir.',
'All right. Your way. Jump onto the new line.':'Peki. Senin yolun. Yeni çizgiye zıpla.',
'Too many teeth. Let me fix that.':'Fazla diş var. Bunu düzelteyim.',
'He changed the rules. So can we. Use this line.':'Kuralları değiştirdi. Biz de değiştiririz. Bu çizgiyi kullan.',
'E  ASK THE ARTIST TO ERASE A FOE (once this room)':'E  RESSAMDAN BİR DÜŞMANI SİLMESİNİ İSTE (bu odada bir kez)',
'DRAW A HEAVY PENCIL':'DEV KALEM ÇİZ','DRAW A HIGH ROAD':'YÜKSEK YOL ÇİZ',
'next lesson...':'sonraki ders...','Who drew the gun?':'Silahı kim çizdi?',
'I did not draw that moon.':'O ayı ben çizmedim.','Someone is cutting the notebook.':'Birisi defteri kesiyor.',
'He has been reading your moves.':'Hareketlerini okuyormuş.',
'a red stroke warns; a blue gap invites':'kırmızı çizgi uyarır; mavi boşluk davet eder',
'a fold that finds its way back':'dönüş yolunu bulan bir katlama',
'SPACE  ^':'SPACE / W / ↑','A / D   ->':'A / D   ->',
'SHIFT / K  ->  leave the red line behind':'SHIFT / K  ->  kırmızı çizgiyi arkanda bırak',
}

from localization_content import TR_CONTENT
from campaign_translations import TR_CAMPAIGN
TR.update(TR_CONTENT)
TR.update(TR_CAMPAIGN)
from localization_combat import TR_COMBAT
TR.update(TR_COMBAT)
from localization_revision import TR_REVISION, PATTERNS_REVISION
TR.update(TR_REVISION)
from localization_de import DE
from localization_it import IT
from localization_clean_pages import CLEAN_PAGES
for source, copies in CLEAN_PAGES.items():
    TR[source], DE[source], IT[source] = copies
from localization_guardians import GUARDIAN_TEXT
for source, copies in GUARDIAN_TEXT.items():
    TR[source], DE[source], IT[source] = copies
from localization_release_041 import RELEASE_041
for source, copies in RELEASE_041.items():
    TR[source], DE[source], IT[source] = copies
CATALOGS = {'tr': TR, 'de': DE, 'it': IT}

# Translate joined labels and variable counters without touching IDs in saves.
PATTERNS = (
 (r'^try (\d+) / crossed out$',r'deneme \1 / silindi'),
 (r'^see page (\d+) ->$',r'sayfa \1 ->'),
 (r'^PHASE (.+)$', r'EVRE \1'),(r'^ORBIT (.+)$',r'YÖRÜNGE \1'),
 (r'^DIRECTOR / ORDER (.+)$',r'YÖNETİCİ / EMİR \1'),(r'^ATTEMPT (.+)$',r'DENEME \1'),
 (r'^REVISION (.+)$',r'DÜZELTME \1'),(r'^COPY: (.+)$',r'KOPYA: \1'),
 (r'^Moved: (.+)$',r'Hareket: \1'),(r'^Jumps: (.+)$',r'Zıplama: \1'),(r'^Dashes: (.+)$',r'Dash: \1'),
 (r'^Targets: (.+)$',r'Hedef: \1'),(r'^Dodges: (.+)$',r'Başarılı kaçış: \1'),
 (r'^LESSON (.+)$',r'EĞİTİM \1'),(r'^PAGE (.+)$',r'SAYFA \1'),(r'^RUNES: (.+)$',r'RÜNLER: \1'),
 (r'^BACK PAGES: (.+)$',r'ESKİZ DEFTERİ: \1'),
 (r'^E  learn (.+)$',lambda m:'E  '+translate(m[1].upper()).lower()+' öğren'),
 (r'^TECHNIQUE LEARNED: (.+?) — (.+)$',lambda m:'TEKNİK ÖĞRENİLDİ: '+translate(m[1])+' — '+translate(m[2])),
 (r'^(TECHNIQUE|LEARNED) / (.+)$',lambda m:('TEKNİK' if m[1]=='TECHNIQUE' else 'ÖĞRENİLDİ')+' / '+translate(m[2])),
 (r'^E  ASK THE ARTIST: (.+)$',lambda m:'E  RESSAMDAN İSTE: '+translate(m[1])),
 (r'^(.+) belonged to this page$',lambda m:translate(m[1])+' bu sayfaya aitti'),
 (r'^(.+) clipped into the notebook$',r'\1 deftere eklendi'),
 (r'^\+(.+) seconds of edge-jump grace\.$',r'+\1 saniye kenar zıplama payı.'),
 (r'^\+(.+) reach on the third blade strike\.$',r'Üçüncü bıçak vuruşuna +\1 erişim.'),
 (r'^\+(.+)% air control; jump height stays the same\.$',r'+%\1 hava kontrolü; zıplama yüksekliği aynı.'),
 (r'^Sidearm reloads take (.+)% less time\.$',r'Tabanca doldurma süresi %\1 kısalır.'),
 (r'^(.+)% narrower pellet spread\.$',r'%\1 daha dar saçılım.'),
 (r'^\+(.+)% scattergun knockback\.$',r'+%\1 pompalı geri itişi.'),
 (r'^One extra target per sidearm bullet\.$',r'Her tabanca mermisine bir ek hedef.'),
 (r'^One extra rebound for Orbit Pulse / Rubber Band\.$',r'Yörünge Darbesi / Lastik Sapan için bir ek sekme.'),
 (r'^Null / Eraser Cannon reloads take (.+)% less time\.$',r'Boşluk / Silgi Topu doldurma süresi %\1 kısalır.'),
 (r'^\+(.+)% Orbit Pulse / Rubber Band projectile lifetime\.$',r'+%\1 Yörünge Darbesi / Lastik Sapan mermi ömrü.'),
 (r'^\+(.+)% sidearm projectile speed\.$',r'+%\1 tabanca mermi hızı.'),
 (r'^Dash recovery is (.+) seconds shorter\.$',r'Dash dolum süresi \1 saniye kısalır.'),
)

PATTERNS = PATTERNS_REVISION + PATTERNS

def translate(text):
    text = str(text)
    if _language == 'en':
        return text
    catalog = CATALOGS[_language]
    if text in catalog:
        return catalog[text]
    from localization_dynamic import translate_dynamic
    result = translate_dynamic(text, _language, translate)
    if result is not None:
        return result
    if _language != 'tr':
        return text
    for pattern,replacement in PATTERNS:
        if re.fullmatch(pattern,text):
            return re.sub(pattern,replacement,text)
    # Joined first-pickup education has two complete source phrases.
    prefix='Lost Sketches are discarded ideas. Keep them to learn lasting tricks across pages. '
    if text.startswith(prefix):
        return TR[prefix.rstrip()]+' '+translate(text[len(prefix):])
    return text

class LocalizedFont:
    """Translate before measuring and wrapping for every selected language."""
    def __init__(self,font):
        self.raw = font
    def render(self,text,*args,**kwargs):
        return self.raw.render(translate(text),*args,**kwargs)
    def size(self,text):
        return self.raw.size(translate(text))
    def __getattr__(self,name):
        return getattr(self.raw,name)
