"""Visible runtime labels and joined combat notices stay in the chosen language."""
import re
import unittest

from advanced_enemies import FinalEditorBoss
from chapters import build_chapter
from identity_content import BOSS_ENCOUNTERS, BOSS_RULES
from localization import TR, get_language, set_language, translate
from sketches import SKETCHES, collection_message
from staging import ENCOUNTERS


class LocalizationRevisionTests(unittest.TestCase):
    def setUp(self):
        self.language=get_language()
        set_language('tr')

    def tearDown(self):
        set_language(self.language)

    def test_actual_five_page_notes_encounters_and_discovery_clues_have_turkish(self):
        sources=set()
        for page in range(5):
            runtime=build_chapter(page)
            sources.update(note.text for note in runtime.world.notes)
            sources.update(doodle[2] for doodle in runtime.world.doodles)
            sources.update(zone.label for zone in runtime.world.zones)
            for entity in runtime.entities.items:
                for field in ('display_name','boss_rule','prompt','invitation','answer','title','caption','label'):
                    value=getattr(entity,field,'')
                    if isinstance(value,str):sources.add(value)
        for pair in ENCOUNTERS.values():sources.update(pair)
        sources.update(pair[1] for pair in BOSS_ENCOUNTERS.values())
        sources.update(BOSS_RULES.values())
        sources.update(FinalEditorBoss.SCENARIO_LABELS.values())
        prose={s for s in sources if re.search('[A-Za-z]{3}',s)}
        self.assertGreater(len(prose),100)
        for source in prose:
            with self.subTest(source=source):
                self.assertTrue(source in TR or translate(source)!=source)
                set_language('en')
                self.assertEqual(translate(source),source)
                set_language('tr')

    def test_joined_counters_translate_the_payload_as_well_as_the_prefix(self):
        expected={
            'wave 2/3':'dalga 2/3',
            'COPY: PENCIL BLADE':'KOPYA: KALEM BIÇAĞI',
            'COPY: FOLDED SHURIKEN':'KOPYA: GERİ DÖNEN KATLAMA',
            'ORBIT 3 / 3 — NEW CONSTELLATION':'YÖRÜNGE 3 / 3 — YENİ TAKIMYILDIZI',
            'E  fold tab 2 (mountain)':'E  2. şeridi katla (tepe)',
            'E  transfer impression 4 (right to left)':'E  4. baskı izini aktar (sağdan sola)',
            'impression 1 already revealed':'1. baskı izi zaten açıldı',
            'STAR  /  12s':'YILDIZ  /  12 sn',
        }
        for source,result in expected.items():
            with self.subTest(source=source):self.assertEqual(translate(source),result)

    def test_every_rune_pickup_translates_its_name_and_effect(self):
        for sketch in SKETCHES:
            text=translate(collection_message(sketch.secret_id))
            with self.subTest(sketch=sketch.secret_id):
                self.assertTrue(text.startswith('TEKNİK ÖĞRENİLDİ: '))
                self.assertNotIn(sketch.technique,text)
                self.assertNotIn('reload',text)
                self.assertNotIn('seconds',text)
                self.assertNotIn('sidearm',text)
                self.assertNotIn('Permanent',text)


if __name__=='__main__':unittest.main()
