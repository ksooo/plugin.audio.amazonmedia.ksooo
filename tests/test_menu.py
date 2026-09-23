"""The menus against the dispatcher.

A menu entry whose mode nobody handles ends in Kodi as an empty, failed
listing. Features have been removed from the add-on; their entries must go
with them.
"""

import unittest

from .support import AddonTest, Kodi, invoke, signed_in
from resources.lib.access import AMaccess
from resources.lib.amzcall import AMcall
from resources.lib.main import AmazonMedia
from resources.lib.menu import AMmenu
from resources.lib.tools import AMtools


def menu_entries():
    for name in sorted(vars(AMmenu)):
        if name.startswith('menu'):
            for entry in getattr(AMmenu, name)():
                yield name, entry['fct']


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


if __name__ == '__main__':
    unittest.main()
