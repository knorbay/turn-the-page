"""Concise guardian warnings, optional duels and permanent rune rewards.

Each canonical English phrase has Turkish, German and Italian copies. Stable
enemy and reward IDs remain in their authored form in saves and factories.
"""

GUARDIAN_TEXT = {
    "ORBIT PULSE ->": ("YÖRÜNGE DARBESİ →", "ORBITALIMPULS →", "IMPULSO ORBITALE →"),
    "OPEN — HIT": ("AÇIK — VUR", "OFFEN — SCHLAG ZU", "ESPOSTO — COLPISCI"),
    "LOOSE SPOKES — HIT": ("TELLER GEVŞEDİ — VUR", "LOSE SPEICHEN — SCHLAG ZU", "RAGGI ALLENTATI — COLPISCI"),
    "ROLL — JUMP": ("YUVARLANIYOR — ZIPLA", "ROLLE — SPRING", "ROTOLA — SALTA"),
    "LEAVE THE LASSO": ("KEMENTTEN ÇIK", "RAUS AUS DEM LASSO", "ESCI DAL LAZO"),
    "JUMP THE SPUR": ("MAHMUZDAN ZIPLA", "SPRING ÜBER DEN SPORN", "SALTA LO SPERONE"),
    "CRACKED SHELL — HIT": ("KABUK ÇATLADI — VUR", "SCHALE GEBROCHEN — SCHLAG ZU", "GUSCIO ROTTO — COLPISCI"),
    "JUMP THE ORBIT": ("HALKADAN ZIPLA", "SPRING ÜBER DEN RING", "SALTA L'ANELLO"),
    "BACK FROM THE CLAW": ("KISKAÇTAN UZAKLAŞ", "WEG VON DER SCHERE", "ALLONTANATI DALLA CHELA"),
    "LEAVE THE CRATER": ("KRATERDEN ÇIK", "RAUS AUS DEM KRATER", "ESCI DAL CRATERE"),
    "TORN COLLAR — HIT": ("TASMA YIRTILDI — VUR", "HALSBAND GERISSEN — SCHLAG ZU", "COLLARE STRAPPATO — COLPISCI"),
    "RUSH — JUMP": ("HÜCUM — ZIPLA", "ANSTURM — SPRING", "CARICA — SALTA"),
    "LEAVE THE STAMP": ("DAMGA İZİNDEN ÇIK", "RAUS AUS DER STEMPELMARKE", "ESCI DAL SEGNO DEL TIMBRO"),
    "DODGE THE COPIES": ("KOPYALARDAN KAÇ", "WEICHE DEN KOPIEN AUS", "SCHIVA LE COPIE"),
    "FOLDED WINGS — HIT": ("KANATLAR KATLANDI — VUR", "FLÜGEL GEFALTET — SCHLAG ZU", "ALI RIPIEGATE — COLPISCI"),
    "BETWEEN THE PAGES": ("SAYFALARIN ARASINDA KAL", "BLEIB ZWISCHEN DEN SEITEN", "RESTA TRA LE PAGINE"),
    "DODGE THE INK DUST": ("MÜREKKEP TOZUNDAN KAÇ", "WEICHE DEM TINTENSTAUB AUS", "SCHIVA LA POLVERE D'INCHIOSTRO"),
    "OUTSIDE THE WINGS": ("KANATLARDAN UZAKLAŞ", "RAUS AUS DER FLÜGELREICHWEITE", "FUORI DALLA PORTATA DELLE ALI"),

    "BRASS TUMBLEWEED": ("PİRİNÇ ÇÖL ÇALISI", "MESSINGSTEPPENLÄUFER", "ROTOLACAMPO D'OTTONE"),
    "ORBIT CRAB": ("YÖRÜNGE YENGECİ", "ORBITKRABBE", "GRANCHIO ORBITALE"),
    "CARBON HOUND": ("KARBON TAZISI", "KARBONSPÜRHUND", "SEGUGIO DI CARBONIO"),
    "DRAFT MOTH": ("TASLAK GÜVESİ", "ENTWURFSMOTTE", "FALENA DELLA BOZZA"),

    "JUMP THE ROLL. LEAVE THE LASSO MARK.": (
        "YUVARLANIRKEN ZIPLA. KEMENT İZİNDEN ÇIK.",
        "SPRING ÜBER DIE ROLLE. VERLASS DIE LASSOMARKE.",
        "SALTA IL ROTOLAMENTO. ESCI DAL SEGNO DEL LAZO."),
    "JUMP THE RING. LEAVE THE CRATER MARK.": (
        "HALKADAN ZIPLA. KRATER İZİNDEN ÇIK.",
        "SPRING ÜBER DEN RING. VERLASS DIE KRATERMARKE.",
        "SALTA L'ANELLO. ESCI DAL SEGNO DEL CRATERE."),
    "JUMP THE RUSH. LEAVE THE STAMP MARK.": (
        "HÜCUMDA ZIPLA. DAMGA İZİNDEN ÇIK.",
        "SPRING BEIM ANSTURM. VERLASS DIE STEMPELMARKE.",
        "SALTA LA CARICA. ESCI DAL SEGNO DEL TIMBRO."),
    "STAY BETWEEN THE PAGES. LEAVE THE WINGS.": (
        "SAYFALARIN ARASINDA KAL. KANATLARDAN UZAKLAŞ.",
        "BLEIB ZWISCHEN DEN SEITEN. WEICHE DEN FLÜGELN AUS.",
        "RESTA TRA LE PAGINE. ALLONTANATI DALLE ALI."),

    "E  challenge brass tumbleweed / optional": (
        "E / pirinç çalıya meydan oku / isteğe bağlı",
        "E / Messingsteppenläufer fordern / optional",
        "E / sfida il rotolacampo / facoltativo"),
    "E  challenge orbit crab / optional": (
        "E / yörünge yengecine meydan oku / isteğe bağlı",
        "E / Orbitkrabbe fordern / optional",
        "E / sfida il granchio orbitale / facoltativo"),
    "E  challenge carbon hound / optional": (
        "E / karbon tazıya meydan oku / isteğe bağlı",
        "E / Karbonspürhund fordern / optional",
        "E / sfida il segugio di carbonio / facoltativo"),
    "E  challenge draft moth / optional": (
        "E / taslak güvesine meydan oku / isteğe bağlı",
        "E / Entwurfsmotte fordern / optional",
        "E / sfida la falena della bozza / facoltativo"),

    "a brass spur from the abandoned high-noon sketch": (
        "terk edilmiş öğle eskizinden bir pirinç mahmuz",
        "ein Messingsporn aus der verworfenen Mittagsskizze",
        "uno sperone d'ottone dallo schizzo scartato di mezzogiorno"),
    "a shell drawn around a forgotten satellite": (
        "unutulmuş bir uydunun çevresine çizilen kabuk",
        "eine Schale um einen vergessenen Satelliten",
        "un guscio disegnato attorno a un satellite dimenticato"),
    "a carbon fang clipped from the rejected case file": (
        "atılmış dava dosyasından koparılan karbon köpek dişi",
        "ein Karbonfangzahn aus der verworfenen Fallakte",
        "una zanna di carbonio ritagliata dal fascicolo scartato"),
    "a moth wing saved from the last discarded draft": (
        "son atılmış taslaktan kurtarılan güve kanadı",
        "ein Mottenflügel aus dem letzten verworfenen Entwurf",
        "un'ala di falena salvata dall'ultima bozza scartata"),

    "THE BRASS SPUR": ("PİRİNÇ MAHMUZ", "DER MESSINGSPORN", "LO SPERONE D'OTTONE"),
    "SPUR RUNE": ("MAHMUZ RÜNÜ", "SPORNRUNE", "RUNA DELLO SPERONE"),
    "Your dash becomes ready a little sooner.": (
        "Atılman biraz daha çabuk hazır olur.",
        "Ausweichen ist etwas früher bereit.",
        "Lo scatto torna pronto un po' prima."),
    "Dash recovery is 0.06 seconds shorter.": (
        "Atılma dolum süresi 0.06 saniye kısalır.",
        "Ausweichen ist 0.06 Sekunden früher bereit.",
        "Recupero dello scatto ridotto di 0.06 secondi."),
    "THE ORBIT SHELL": ("YÖRÜNGE KABUĞU", "DIE ORBITSCHALE", "IL GUSCIO ORBITALE"),
    "SHELL RUNE": ("KABUK RÜNÜ", "SCHALENRUNE", "RUNA DEL GUSCIO"),
    "Ricochet shots stay in flight a little longer.": (
        "Sekmeli atışlar biraz daha uzun süre uçar.",
        "Abpraller bleiben etwas länger in der Luft.",
        "I colpi a rimbalzo restano in volo un po' più a lungo."),
    "+20% Orbit Pulse / Rubber Band projectile lifetime.": (
        "+%20 Yörünge Darbesi / Lastik Sapan mermi ömrü.",
        "+20% Flugzeit für Orbitalimpuls / Gummiband.",
        "+20% durata proiettili di Impulso Orbitale / Elastico."),
    "THE CARBON FANG": ("KARBON KÖPEK DİŞİ", "DER KARBONFANGZAHN", "LA ZANNA DI CARBONIO"),
    "FANG RUNE": ("DİŞ RÜNÜ", "FANGZAHNRUNE", "RUNA DELLA ZANNA"),
    "Reload your sidearm a little faster.": (
        "Tabancanı biraz daha hızlı doldur.",
        "Lade deine Pistole etwas schneller nach.",
        "Ricarica la pistola un po' più in fretta."),
    "Sidearm reloads take 10% less time.": (
        "Tabanca doldurma süresi %10 kısalır.",
        "Pistole: 10% weniger Nachladezeit.",
        "Ricarica pistola: 10% di tempo in meno."),
    "THE DRAFT WING": ("TASLAK KANADI", "DER ENTWURFSFLÜGEL", "L'ALA DELLA BOZZA"),
    "WING RUNE": ("KANAT RÜNÜ", "FLÜGELRUNE", "RUNA DELL'ALA"),
    "Your blade finisher reaches a little farther.": (
        "Bıçak bitirişin biraz daha uzağa erişir.",
        "Dein letzter Klingenhieb reicht etwas weiter.",
        "Il colpo finale della lama arriva un po' più lontano."),
    "+12 reach on the third blade strike.": (
        "Üçüncü bıçak vuruşuna +12 erişim.",
        "+12 Reichweite beim dritten Klingenhieb.",
        "+12 portata al terzo colpo della lama."),
}
