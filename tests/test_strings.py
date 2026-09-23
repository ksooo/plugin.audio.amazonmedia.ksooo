"""The language files against each other and against the code that uses them."""

import glob
import os
import re
import unittest

from .support import LANGUAGE_FOLDER, ROOT, SOURCE_LANGUAGE, TRANSLATIONS

_ENTRY = re.compile(r'^msgctxt "#(\d+)"\nmsgid (".*")\nmsgstr (".*")$', re.M)

# German words that are the same in English.
SAME_IN_GERMAN = {'"Songs"'}


def entries(language):
    path = os.path.join(LANGUAGE_FOLDER, 'resource.language.%s' % language, 'strings.po')
    with open(path, encoding='utf-8') as handle:
        body = handle.read()
    found = {int(number): (msgid, msgstr) for number, msgid, msgstr in _ENTRY.findall(body)}
    # A string wrapped over several lines would be dropped by the pattern
    # rather than reported, which would make every test below pass wrongly.
    assert len(found) == body.count('\nmsgctxt '), language
    return found


def ids_in_use():
    """Every string id the add-on refers to, in its code and in its settings."""
    used = set()
    for path in glob.glob(os.path.join(ROOT, 'resources', 'lib', '*.py')):
        with open(path, encoding='utf-8') as handle:
            used.update(int(number) for number in re.findall(r'\b(3\d{4})\b', handle.read()))
    with open(os.path.join(ROOT, 'resources', 'settings.xml'), encoding='utf-8') as handle:
        used.update(int(number) for number in re.findall(r'label="(3\d{4})"', handle.read()))
    return used


class Code(unittest.TestCase):
    def test_every_string_the_add_on_uses_exists(self):
        self.assertEqual(ids_in_use() - set(entries(SOURCE_LANGUAGE)), set())

    def test_no_string_is_left_behind_unused(self):
        self.assertEqual(set(entries(SOURCE_LANGUAGE)) - ids_in_use(), set())


class Languages(unittest.TestCase):
    def test_a_translation_carries_the_same_ids(self):
        for language in TRANSLATIONS:
            with self.subTest(language=language):
                self.assertEqual(set(entries(language)), set(entries(SOURCE_LANGUAGE)))

    def test_a_translation_keeps_the_english_source(self):
        english = entries(SOURCE_LANGUAGE)
        for language in TRANSLATIONS:
            with self.subTest(language=language):
                differing = {number for number, (msgid, _) in entries(language).items()
                             if msgid != english[number][0]}
                self.assertEqual(differing, set())

    def test_english_is_the_source_and_translates_nothing(self):
        translated = {number for number, (_, msgstr) in entries(SOURCE_LANGUAGE).items() if msgstr != '""'}
        self.assertEqual(translated, set())

    def test_nothing_is_left_in_english_in_german(self):
        english = {number: (msgid, msgstr) for number, (msgid, msgstr) in entries('de_de').items()
                   if msgstr in ('""', msgid) and msgstr not in SAME_IN_GERMAN}
        self.assertEqual(english, {})


if __name__ == '__main__':
    unittest.main()
