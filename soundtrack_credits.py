"""Paginated, readable attribution for the selected recordings."""
from __future__ import annotations

import pygame

from paper_renderer import jitter_line
from localization import normalize_language



CREDIT_COPY = {
    "tr": ("MÜZİK KÜNYESİ", "Bölüm ve boss kayıtları · ← / →", "Kaynak / ",
           "4. ve 5. sayfanın keşif müzikleri oyuna özel defter besteleridir.", "ESC / GERİ", "Eser adları özgün dilinde korunmuştur."),
    "en": ("MUSIC CREDITS", "Page and boss recordings · ← / →", "Source / ",
           "Pages 4 and 5 use original notebook compositions for exploration.", "ESC / BACK", "Recording titles retain their original spelling."),
    "de": ("MUSIKNACHWEISE", "Aufnahmen für Seiten und Bosse · ← / →", "Quelle / ",
           "Die Erkundungsmusik auf Seite 4 und 5 wurde eigens für das Spiel komponiert.", "ESC / ZURÜCK", "Die Titel der Aufnahmen bleiben in ihrer Originalsprache."),
    "it": ("CREDITI MUSICALI", "Musica delle pagine e dei boss · ← / →", "Fonte / ",
           "La musica di esplorazione delle pagine 4 e 5 è composta per il gioco.", "ESC / INDIETRO", "I titoli delle registrazioni mantengono la grafia originale."),
}

CREDITS_BACK_RECT = pygame.Rect(868, 632, 188, 44)
CREDITS_PREVIOUS_RECT = pygame.Rect(510, 632, 82, 44)
CREDITS_NEXT_RECT = pygame.Rect(714, 632, 82, 44)
CREDITS_PER_PAGE = 6
INK = (55, 51, 48)
RED = (130, 57, 53)
EDIT_NOTE = {
    "tr": "Oyun için döngü ve ses seviyesi düzenlendi.",
    "en": "Loop and playback level edited for the game.",
    "de": "Schleife und Lautstärke für das Spiel angepasst.",
    "it": "Loop e volume adattati per il gioco.",
}


def _raw_font(localized):
    # Track titles, names and source identifiers are attribution, so keep
    # their exact spelling independent of the game's translation dictionary.
    return getattr(localized, "raw", localized)


def _text(surface, font, value, position, color=INK, max_width=None):
    image = font.render(str(value), True, color)
    if max_width and image.get_width() > max_width:
        image = pygame.transform.smoothscale(image, (max_width,
            round(image.get_height()*max_width/image.get_width())))
    surface.blit(image, position)
    return image.get_rect(topleft=position)


def unique_music_credits(credits):
    unique, seen = [], set()
    for item in credits:
        key = (item.get("title", ""), item.get("composer", ""))
        if key[0] and key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def music_credit_page_count(credits):
    return max(1, (len(unique_music_credits(credits))+CREDITS_PER_PAGE-1)//CREDITS_PER_PAGE)


def _url_lines(value, font, width):
    # Wrap source identifiers at slash boundaries instead of shrinking them.
    lines, line = [], ""
    for part in str(value).split("/"):
        candidate = line + ("/" if line else "") + part
        if line and font.size(candidate)[0] > width:
            lines.append(line+"/")
            line = part
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines[:3]


def draw_music_credits(surface, renderer, credits, language="tr", page=0):
    """Draw a full music credit page from scene_music.MUSIC_CREDITS.

    ``credits`` contains title/composer/source_url/license_url dictionaries.
    ``source`` remains accepted for older metadata. Proper titles, composers,
    source-pack URLs and licences come from those records; navigation is
    owned by Game, not this helper.
    """
    title, description, source_label, score_note, back, titles_note = CREDIT_COPY[normalize_language(language)]
    renderer.background(surface, 4)
    title_font = _raw_font(renderer.font)
    list_font = _raw_font(renderer.font_small)
    face = pygame.font.match_font("arial,dejavusans,liberationsans")
    small = pygame.font.Font(face, 17)
    identifier_font = pygame.font.Font(face, 14)
    renderer.rough_rect(surface, (160, 149, 126),
                        pygame.Rect(46, 30, 1028, 582), 1, 8491)
    _text(surface, title_font, title, (76, 46), RED)
    _text(surface, small,
          description,
          (76, 99), max_width=958)
    # Two columns preserve the proper names at game scale. Duplicate source
    # roles (a recording used for both a scene and boss) are credited once.
    pages = music_credit_page_count(credits)
    page = int(page) % pages
    unique = unique_music_credits(credits)[page*CREDITS_PER_PAGE:(page+1)*CREDITS_PER_PAGE]
    for index, item in enumerate(unique):
        column, row = divmod(index, 3)
        left = 77 + column*497
        y = 143+row*126
        _text(surface, list_font, item["title"], (left, y), max_width=464)
        _text(surface, small,
              str(item.get("composer", "")) + "  ·  " + str(item.get("license", "")),
              (left, y+27), (117, 110, 94), max_width=464)
        source_url = item.get("source_url", item.get("source", ""))
        for line_index, line in enumerate(_url_lines(source_url, identifier_font, 464)):
            _text(surface, identifier_font, line, (left, y+52+line_index*17))
        if item.get("changes"):
            _text(surface, identifier_font, EDIT_NOTE[normalize_language(language)],
                  (left, y+94), (117, 110, 94), max_width=464)
        jitter_line(surface, (206, 193, 165), (left, y+113),
                    (left+466, y+113), 1, 8510+index, 1, .4)
    licenses = list(dict.fromkeys(str(item.get("license_url", ""))
                                 for item in unique if item.get("license_url")))
    license_names = list(dict.fromkeys(str(item.get("license", ""))
                                     for item in unique if item.get("license")))
    for index, (name, url) in enumerate(zip(license_names, licenses)):
        _text(surface, identifier_font, name + "  ·  " + url,
              (77, 527+index*18), max_width=958)
    _text(surface, small, score_note,
          (77, 586), max_width=958)
    button = CREDITS_BACK_RECT
    pygame.draw.rect(surface, (247, 241, 219), button)
    renderer.rough_rect(surface, RED, button, 1, 8587)
    label = back
    label_image = list_font.render(label, True, INK)
    surface.blit(label_image, label_image.get_rect(center=button.center))
    _text(surface, small,
          titles_note,
          (76, 645), (117, 110, 94), max_width=416)
    for rect, label in ((CREDITS_PREVIOUS_RECT, "←"), (CREDITS_NEXT_RECT, "→")):
        pygame.draw.rect(surface, (247, 241, 219), rect)
        renderer.rough_rect(surface, RED, rect, 1, 8590)
        image = list_font.render(label, True, INK)
        surface.blit(image, image.get_rect(center=rect.center))
    _text(surface, small, f"{page+1} / {pages}", (624, 645))
    return button.copy()


__all__ = ["draw_music_credits", "CREDITS_BACK_RECT", "CREDITS_PREVIOUS_RECT",
           "CREDITS_NEXT_RECT", "music_credit_page_count"]
