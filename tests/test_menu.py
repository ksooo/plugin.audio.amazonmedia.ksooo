"""The menus against the dispatcher and against the language files.

A menu entry whose mode nobody handles ends in Kodi as an empty, failed
listing. Features have been removed from the add-on; their entries must go
with them.
"""

import os
import re
import unittest

from .support import LANGUAGE_FOLDER, LANGUAGES, AddonTest, Kodi, invoke, signed_in, text
from resources.lib.access import AMaccess
from resources.lib.amzcall import AMcall
from resources.lib.main import AmazonMedia
from resources.lib.menu import AMmenu
from resources.lib.tools import AMtools

# Languages that set a space before a colon; the others set none.
SPACE_BEFORE_COLON = {'fr_fr'}


def menu_entries():
    for name in sorted(vars(AMmenu)):
        if name.startswith('menu'):
            for entry in getattr(AMmenu, name)():
                yield name, entry['fct']


def shown(language):
    """What Kodi shows for each string id in the given language."""
    path = os.path.join(LANGUAGE_FOLDER, 'resource.language.%s' % language, 'strings.po')
    with open(path, encoding='utf-8') as handle:
        return {int(number): msgstr or msgid
                for number, msgid, msgstr in re.findall(r'msgctxt "#(\d+)"\nmsgid "(.*)"\nmsgstr "(.*)"', handle.read())}


class Menus(AddonTest):
    def test_every_entry_lists_something_or_asks_amazon(self):
        for menu, mode in menu_entries():
            with self.subTest(menu=menu, mode=mode):
                Kodi.typed = 'jazz'
                del Kodi.items[:]
                invoke('mode=' + mode)
                self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
                asked = self.patch(AMcall, 'amzCall', side_effect=RuntimeError('not answered in this test'))
                AmazonMedia().reqDispatch()
                self.assertTrue(asked.called or Kodi.items, 'nothing handles this entry')

    def test_the_search_dialog_says_what_is_searched_for(self):
        # The menu entry is just "Search"; the dialog has no path above it to tell what for.
        for mode, heading in (('searchPlayLists', 30013), ('searchAlbums', 30010),
                              ('searchSongs', 30011), ('searchArtist', 30014)):
            with self.subTest(mode=mode):
                del Kodi.headings[:]
                invoke('mode=' + mode)
                self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
                AmazonMedia().reqDispatch()
                self.assertEqual(Kodi.headings, [text(heading)])
                self.assertNotEqual(text(heading), text(30042))


class Labels(unittest.TestCase):
    def test_no_entry_repeats_the_name_of_its_menu(self):
        # The path top left names the menu already. A word that begins like the menu
        # name also catches "Playlist" below "Playlists" and "Album" below "Albums".
        menus = {entry['fct']: entry['txt'] for entry in AMmenu.menuHome() if entry['fct'].startswith('menu')}
        for language in LANGUAGES:
            texts = shown(language)
            for menu, name in menus.items():
                stem = texts[name].lower()[:5]
                for entry in getattr(AMmenu, menu)():
                    with self.subTest(language=language, menu=texts[name], entry=texts[entry['txt']]):
                        words = re.findall(r'\w+', texts[entry['txt']].lower())
                        self.assertFalse([word for word in words if word.startswith(stem)])

    def test_the_search_entry_says_that_a_dialog_follows(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertTrue(shown(language)[30042].endswith(' ...'))

    def test_the_number_of_a_recent_search_reads_as_a_number(self):
        # No dash that makes it read as negative, and a colon set as the language sets it.
        for language in LANGUAGES:
            texts = shown(language)
            colon = r'\d :' if language in SPACE_BEFORE_COLON else r'\d:'
            for number in (30032, 30033, 30034):
                with self.subTest(language=language, label=texts[number]):
                    self.assertNotRegex(texts[number], r'-\s*\d')
                    self.assertRegex(texts[number], colon)


if __name__ == '__main__':
    unittest.main()
