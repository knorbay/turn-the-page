"""Language-aware joined labels; substitutions preserve gameplay numbers."""
from __future__ import annotations
import re

# Captured numbers never enter the dictionaries, so all saves and counters keep
# their original values. Phrase captures are translated recursively at runtime.
PATTERN_COPIES = (
    (r'try (\d+) / crossed out', 'deneme {0} / silindi', 'Versuch {0} / durchgestrichen', 'tentativo {0} / cancellato'),
    (r'see page (\d+) ->', 'sayfa {0} ->', 'siehe Seite {0} ->', 'vedi pagina {0} ->'),
    (r'PHASE (.+)', 'EVRE {0}', 'PHASE {0}', 'FASE {0}'),
    (r'ORBIT (\d+) / (\d+) — NEW CONSTELLATION', 'YÖRÜNGE {0} / {1} — YENİ TAKIMYILDIZI', 'UMLAUF {0} / {1} — NEUES STERNBILD', 'ORBITA {0} / {1} — NUOVA COSTELLAZIONE'),
    (r'ORBIT (.+)', 'YÖRÜNGE {0}', 'UMLAUF {0}', 'ORBITA {0}'),
    (r'DIRECTOR / ORDER (.+)', 'YÖNETİCİ / EMİR {0}', 'DIREKTOR / BEFEHL {0}', 'DIRETTORE / ORDINE {0}'),
    (r'ATTEMPT (.+)', 'DENEME {0}', 'VERSUCH {0}', 'TENTATIVO {0}'),
    (r'REVISION (.+)', 'DÜZELTME {0}', 'KORREKTUR {0}', 'REVISIONE {0}'),
    (r'COPY: (.+)', 'KOPYA: {0}', 'KOPIE: {0}', 'COPIA: {0}'),
    (r'Moved: (.+)', 'Hareket: {0}', 'Bewegt: {0}', 'Movimento: {0}'),
    (r'Jumps: (.+)', 'Zıplama: {0}', 'Sprünge: {0}', 'Salti: {0}'),
    (r'Dashes: (.+)', 'Atılma: {0}', 'Ausweichen: {0}', 'Scatti: {0}'),
    (r'Targets: (.+)', 'Hedef: {0}', 'Ziele: {0}', 'Bersagli: {0}'),
    (r'Dodges: (.+)', 'Başarılı kaçış: {0}', 'Ausgewichen: {0}', 'Schivate: {0}'),
    (r'LESSON (.+)', 'EĞİTİM {0}', 'LEKTION {0}', 'LEZIONE {0}'),
    (r'PAGE (.+)', 'SAYFA {0}', 'SEITE {0}', 'PAGINA {0}'),
    (r'RUNES: (.+)', 'RÜNLER: {0}', 'RUNEN: {0}', 'RUNE: {0}'),
    (r'BACK PAGES: (.+)', 'ESKİZ DEFTERİ: {0}', 'SKIZZENBUCH: {0}', 'ALBUM: {0}'),
    (r'E  learn (.+)', 'E / {0} öğren', 'E / {0} lernen', 'E / impara {0}'),
    (r'TECHNIQUE LEARNED: (.+?) — (.+)', 'TEKNİK ÖĞRENİLDİ: {0} — {1}', 'TECHNIK GELERNT: {0} — {1}', 'TECNICA APPRESA: {0} — {1}'),
    (r'TECHNIQUE / (.+)', 'TEKNİK / {0}', 'TECHNIK / {0}', 'TECNICA / {0}'),
    (r'LEARNED / (.+)', 'ÖĞRENİLDİ / {0}', 'GELERNT / {0}', 'APPRESA / {0}'),
    (r'E  ASK THE ARTIST: (.+)', 'E / RESSAMDAN İSTE: {0}', 'E / ZEICHNER BITTEN: {0}', 'E / CHIEDI AL DISEGNATORE: {0}'),
    (r'(.+) belonged to this page', '{0} bu sayfaya aitti', '{0} gehörte zu dieser Seite', '{0} apparteneva a questa pagina'),
    (r'(.+) clipped into the notebook', '{0} deftere eklendi', '{0} ins Skizzenbuch geheftet', '{0} aggiunto all\'album'),
    (r'\+(.+) seconds of edge-jump grace\.', '+{0} saniye kenar zıplama payı.', '+{0} Sekunden Sprungfrist an Kanten.', '+{0} secondi di margine per saltare dal bordo.'),
    (r'\+(.+) reach on the third blade strike\.', 'Üçüncü bıçak vuruşuna +{0} erişim.', '+{0} Reichweite beim dritten Klingenhieb.', '+{0} portata al terzo colpo della lama.'),
    (r'\+(.+)% air control; jump height stays the same\.', '+%{0} hava kontrolü; zıplama yüksekliği aynı.', '+{0}% Luftkontrolle; Sprunghöhe bleibt gleich.', '+{0}% controllo in aria; altezza del salto invariata.'),
    (r'Sidearm reloads take (.+)% less time\.', 'Tabanca doldurma süresi %{0} kısalır.', 'Pistole: {0}% weniger Nachladezeit.', 'Ricarica pistola: {0}% di tempo in meno.'),
    (r'(.+)% narrower pellet spread\.', '%{0} daha dar saçılım.', '{0}% engere Schrotstreuung.', 'Dispersione dei pallini ridotta del {0}%.'),
    (r'\+(.+)% scattergun knockback\.', '+%{0} pompalı geri itişi.', '+{0}% Schrotflintenstoß auf Gegner.', '+{0}% spinta del fucile a pallettoni.'),
    (r'One extra target per sidearm bullet\.', 'Her tabanca mermisine bir ek hedef.', 'Ein zusätzliches Ziel pro Pistolenkugel.', 'Un bersaglio extra per proiettile di pistola.'),
    (r'One extra rebound for Orbit Pulse / Rubber Band\.', 'Yörünge Darbesi / Lastik Sapan için bir ek sekme.', 'Ein zusätzlicher Abpraller für Orbitalimpuls / Gummiband.', 'Un rimbalzo extra per Impulso Orbitale / Elastico.'),
    (r'Null / Eraser Cannon reloads take (.+)% less time\.', 'Boşluk / Silgi Topu doldurma süresi %{0} kısalır.', 'Null- / Radiererkanone: {0}% weniger Nachladezeit.', 'Ricarica Cannone Vuoto / Gomma: {0}% di tempo in meno.'),
    (r'\+(.+)% Orbit Pulse / Rubber Band projectile lifetime\.', '+%{0} Yörünge Darbesi / Lastik Sapan mermi ömrü.', '+{0}% Flugzeit für Orbitalimpuls / Gummiband.', '+{0}% durata proiettili di Impulso Orbitale / Elastico.'),
    (r'\+(.+)% sidearm projectile speed\.', '+%{0} tabanca mermi hızı.', '+{0}% Pistolenkugeltempo.', '+{0}% velocità dei proiettili di pistola.'),
    (r'Dash recovery is (.+) seconds shorter\.', 'Atılma dolum süresi {0} saniye kısalır.', 'Ausweichen ist {0} Sekunden früher bereit.', 'Recupero dello scatto ridotto di {0} secondi.'),
    (r'TOOL ADDED — (.+) / Q to try it', 'ARAÇ EKLENDİ — {0} / Q ile dene', 'WERKZEUG ERHALTEN — {0} / mit Q testen', 'ARMA AGGIUNTA — {0} / Q per provarla'),
    (r'wave (\d+)/(\d+)', 'dalga {0}/{1}', 'Welle {0}/{1}', 'ondata {0}/{1}'),
    (r'clue: (.+)', 'ipucu: {0}', 'Hinweis: {0}', 'indizio: {0}'),
    (r'crease clue:  (.+)', 'katlama ipucu:  {0}', 'Falthinweis: {0}', 'indizio della piega: {0}'),
    (r'STAR  /  (.+)s', 'YILDIZ  /  {0} sn', 'STERN  /  {0} s', 'STELLA  /  {0} s'),
    (r'E  fold tab (\d+) \((mountain|valley)\)', 'E  {0}. şeridi katla ({1})', 'E / Lasche {0} falten ({1})', 'E / piega la linguetta {0} ({1})'),
    (r'E  rub impression (\d+)', 'E  {0}. baskı izini ov', 'E / Druckmarke {0} freireiben', 'E / strofina l\'impronta {0}'),
    (r'impression (\d+) already revealed', '{0}. baskı izi zaten açıldı', 'Druckmarke {0} schon aufgedeckt', 'impronta {0} già rivelata'),
    (r'E  transfer impression (\d+) \(right to left\)', 'E  {0}. baskı izini aktar (sağdan sola)', 'E / Druckmarke {0} übertragen (rechts nach links)', 'E / trasferisci l\'impronta {0} (da destra a sinistra)'),
    (r'E  take (.+)', 'E  {0} al', 'E / {0} nehmen', 'E / prendi {0}'),
    (r'NEW DRAWING — (.+)', 'YENİ ÇİZİM — {0}', 'NEUE ZEICHNUNG — {0}', 'NUOVO DISEGNO — {0}'),
    (r'FIELD NOTES / (.+)', 'SAHA NOTLARI / {0}', 'FELDNOTIZEN / {0}', 'APPUNTI / {0}'),
    (r'(.+?) ->', '{0} ->', '{0} ->', '{0} ->'),
)
PATTERNS = tuple((re.compile(pattern), copies) for pattern, *copies in PATTERN_COPIES)
_LANGUAGE_COLUMN = {'tr': 0, 'de': 1, 'it': 2}


def translate_dynamic(text, language, translate):
    for pattern, copies in PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            values = [translate(value) for value in match.groups()]
            # Pickups author lower-case technique names, while the sketchbook
            # stores their headings in capitals. Localize before lowering,
            # including Turkish's dotted and dotless I.
            if pattern.pattern == r'E  learn (.+)':
                title = translate(match[1].upper())
                if language == 'tr':
                    title = title.replace('I', 'ı').replace('İ', 'i')
                values[0] = title.lower()
            return copies[_LANGUAGE_COLUMN[language]].format(*values)
    prefix = 'Lost Sketches are discarded ideas. Keep them to learn lasting tricks across pages. '
    if text.startswith(prefix):
        return translate(prefix.rstrip())+' '+translate(text[len(prefix):])
    # Multi-line cards/dialogue must localize every complete line, while already
    # translated lines stay untouched on the measuring/rendering second pass.
    if '\n' in text:
        return '\n'.join(translate(line) for line in text.split('\n'))
    return None
