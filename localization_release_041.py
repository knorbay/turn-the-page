"""Concise additions to the four-language catalog for the revised combat release."""
RELEASE_041 = {
    'New drawing. Q to try it.': ('Yeni çizim. Q ile dene.', 'Neue Zeichnung. Mit Q ausprobieren.', 'Nuovo disegno. Provalo con Q.'),
    'THE ARTIST IS DRAWING': ('RESSAM ÇİZİYOR', 'DER ZEICHNER ZEICHNET', 'IL DISEGNATORE STA DISEGNANDO'),
    'SECOND DRAFT': ('İKİNCİ TASLAK', 'ZWEITER ENTWURF', 'SECONDA BOZZA'),
    'FOLD CROSSBOW': ('KATLAMA ARBALETİ', 'FALTARMBRUST', 'BALESTRA DI CARTA'),
    'BAMBOO CROSSBOW': ('BAMBU ARBALETİ', 'BAMBUSARMBRUST', 'BALESTRA DI BAMBÙ'),
    'ORBIT SAW': ('YÖRÜNGE TESTERESİ', 'ORBITSÄGE', 'SEGA ORBITALE'),
    'REVISION WHEEL': ('DÜZELTME ÇARKI', 'KORREKTURRAD', 'RUOTA DI REVISIONE'),
    'impact splits the bolt · one shot, then reload': ('darbe oku böler · tek atış, sonra doldur', 'Aufprall spaltet den Bolzen · ein Schuss, dann nachladen', "l’impatto divide il dardo · un colpo, poi ricarica"),
    'throw a ring · two cuts where it stops': ('halkayı at · durduğu yerde iki kesiş', 'Ring werfen · zwei Schnitte am Haltepunkt', 'lancia un anello · due tagli dove si ferma'),
    'A new drawing for the next fight. Q tries it; your weapon stays.': ('Sonraki dövüş için yeni çizim. Q ile dene; elindeki silah değişmez.', 'Eine neue Zeichnung für den nächsten Kampf. Mit Q ausprobieren; deine Waffe bleibt.', 'Un nuovo disegno per il prossimo scontro. Provalo con Q; la tua arma resta.'),
    'REPLAY PAGES': ('SAYFALARI YENİDEN OYNA', 'SEITEN ERNEUT SPIELEN', 'RIGIOCA LE PAGINE'),
    'Your learned sketches stay with you.': ('Öğrendiğin eskizler seninle kalır.', 'Deine erlernten Skizzen bleiben erhalten.', 'Gli schizzi appresi restano con te.'),
    'AFTERWORD': ('SON SÖZ', 'NACHWORT', 'EPILOGO'),
    'A few lines are still yours to draw.': ('Birkaç çizgiyi de sen çiz.', 'Ein paar Linien gehören noch dir.', 'Qualche linea spetta ancora a te.'),
    'THE ROADS I KEPT': ('YANIMDAKİ YOLLAR', 'MEINE BEWAHRTEN WEGE', 'LE STRADE CHE HO TENUTO'),
    'Every wrong turn left a useful line.': ('Her yanlış dönüş işe yarayan bir çizgi bıraktı.', 'Jede falsche Abzweigung hinterließ eine nützliche Linie.', 'Ogni svolta sbagliata ha lasciato una linea utile.'),
    'THE SKY I REACHED': ('ULAŞTIĞIM GÖKYÜZÜ', 'MEIN ERREICHTER HIMMEL', 'IL CIELO CHE HO RAGGIUNTO'),
    'Even a copied line can point somewhere new.': ('Kopya bir çizgi bile yeni bir yön gösterebilir.', 'Auch eine kopierte Linie kann einen neuen Weg weisen.', 'Anche una linea copiata può indicare una nuova direzione.'),
    'THE FIGURE I CHOSE': ('SEÇTİĞİM FİGÜR', 'MEINE GEWÄHLTE FIGUR', 'LA FIGURA CHE HO SCELTO'),
    'The old drafts taught me how to draw myself.': ('Eski taslaklar kendimi çizmeyi öğretti.', 'Die alten Entwürfe lehrten mich, mich selbst zu zeichnen.', 'Le vecchie bozze mi hanno insegnato a disegnare me stesso.'),
    'Leave room for every memory.': ('Her hatıraya yer aç.', 'Lass Platz für jede Erinnerung.', 'Lascia spazio a ogni ricordo.'),
    'THESE LINES ARE MINE': ('BU ÇİZGİLER BENİM', 'DIESE LINIEN SIND MEINE', 'QUESTE LINEE SONO MIE'),
    'PAD-Y / SIGN THE PAGE': ('PAD-Y / SAYFAYI İMZALA', 'PAD-Y / SEITE SIGNIEREN', 'PAD-Y / FIRMA LA PAGINA'),
    'E / SIGN THE PAGE': ('E / SAYFAYI İMZALA', 'E / SEITE SIGNIEREN', 'E / FIRMA LA PAGINA'),
    'YOUR NOTEBOOK IS COMPLETE': ('DEFTERİN TAMAMLANDI', 'DEIN NOTIZBUCH IST VOLLSTÄNDIG', 'IL TUO TACCUINO È COMPLETO'),
    'The next blank page can wait.': ('Sonraki boş sayfa bekleyebilir.', 'Die nächste leere Seite kann warten.', 'La prossima pagina bianca può aspettare.'),
    'THE LAST PAGE': ('SON SAYFA', 'DIE LETZTE SEITE', 'L’ULTIMA PAGINA'),
    'PAD-Y / DRAW': ('PAD-Y / ÇİZ', 'PAD-Y / ZEICHNEN', 'PAD-Y / DISEGNA'),
    'E / DRAW': ('E / ÇİZ', 'E / ZEICHNEN', 'E / DISEGNA'),
}

# Keep the finite pickup notices in the catalog as complete phrases, so a
# translated name and its command are wrapped and measured together.
for _tool in ('FOLD CROSSBOW', 'BAMBOO CROSSBOW', 'ORBIT SAW', 'REVISION WHEEL'):
    _tr, _de, _it = RELEASE_041[_tool]
    RELEASE_041['E  take '+_tool] = ('E  '+_tr+' al', 'E / '+_de+' nehmen', 'E / prendi '+_it)
    RELEASE_041['NEW DRAWING — '+_tool] = ('YENİ ÇİZİM — '+_tr, 'NEUE ZEICHNUNG — '+_de, 'NUOVO DISEGNO — '+_it)
