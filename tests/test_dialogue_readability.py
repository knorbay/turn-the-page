"""Live Artist dialogue leaves the road clear and retains both language copies."""
import ast
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame

from localization import get_language, set_language, translate
from notebook_art import NotebookMaterial
from settings import WIDTH, HEIGHT


class DialogueReadabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.notebook=NotebookMaterial()
        cls.canvas=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)

    def setUp(self):
        self.language=get_language()

    def tearDown(self):
        set_language(self.language)

    def test_artist_note_does_not_cover_the_player_road_or_interaction_prompt(self):
        self.canvas.fill((0,0,0,0))
        self.notebook.artist_note(self.canvas,
            'I left that edge too faint. I have redrawn the landing.','E: nod back')
        painted=pygame.mask.from_surface(self.canvas)
        bounds=painted.get_bounding_rects()
        self.assertTrue(bounds)
        for rect in bounds:
            self.assertGreaterEqual(rect.top,604)
            self.assertGreaterEqual(rect.left,412)
            self.assertLessEqual(rect.right,936)
            self.assertLessEqual(rect.bottom,HEIGHT-8)
        # The old 820px patch at y=218 must stay entirely transparent.
        self.assertEqual(self.canvas.get_at((560,250)).a,0)

    def test_all_authored_notes_fit_a_compact_card_without_losing_words(self):
        root=Path(__file__).resolve().parents[1]
        sources=set()
        for name in ('major_update.py','page_experiences.py','notebook_agency.py','major_campaign.py'):
            module=ast.parse((root/name).read_text())
            sources.update(node.value for node in ast.walk(module)
                if isinstance(node,ast.Constant) and isinstance(node.value,str)
                and len(node.value)>45 and '\n' not in node.value)
        self.assertGreater(len(sources),50)
        for language in ('en','tr'):
            set_language(language)
            for source in sources:
                with self.subTest(language=language,text=source):
                    rect,lines,font,_,_=self.notebook.artist_note_layout(self.canvas,source)
                    self.assertLessEqual(rect.height,90)
                    self.assertEqual(' '.join(lines),' '.join(translate(source).split()))
                    self.assertTrue(all(font.size(line)[0]<=rect.width-24 for line in lines))
                    self.assertLessEqual(23+(len(lines)-1)*max(19,font.get_height())+
                                         font.get_height(),rect.height)

    def test_reply_and_speaker_translate_before_layout(self):
        set_language('tr')
        _,lines,_,label,reply=self.notebook.artist_note_layout(self.canvas,
            'I left that edge too faint. I have redrawn the landing.','E: nod back')
        self.assertEqual(label,'Ressam:')
        self.assertEqual(reply,translate('E: nod back'))
        self.assertEqual(' '.join(lines),translate(
            'I left that edge too faint. I have redrawn the landing.'))


if __name__=='__main__':
    unittest.main()
