"""The path to the current folder, which the skin shows top left after the add-on name."""

import json
import unittest
from urllib.parse import parse_qs, urlencode, urlparse

from .support import AddonTest, Kodi, clicked, invoke, signed_in
from resources.lib.access import AMaccess
from resources.lib.amzcall import AMcall
from resources.lib.item import AMitem
from resources.lib.main import AmazonMedia
from resources.lib.tools import AMtools

PLAYLIST = {'asin': 'B0PLAYLIST', 'playlistId': 'playlist-id', 'title': 'Cool Jazz',
            'trackCount': 70, 'durationSeconds': 20775}
TRACK = {'asin': 'B0CATALOG1', 'title': 'Take Five', 'isMusicSubscription': 'true'}

# Enough of every answer for a listing to come through empty.
NOTHING = {'albumList': [], 'artistList': [], 'playlistList': [], 'trackList': [], 'resultList': [],
           'nextTokenMap': {}, 'results': [{'hits': [], 'nextPage': None}]}


class Breadcrumb(AddonTest):
    def setUp(self):
        super().setUp()
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.answer = NOTHING
        self.patch(AMcall, 'amzCall', side_effect=lambda *args: self.answer)

    def open(self, query):
        del Kodi.items[:]
        invoke(query)
        AmazonMedia().reqDispatch()
        return Kodi.category

    def follow(self, mode):
        """Open the listed folder of the given mode, as a click on it does."""
        for url, li, folder in list(Kodi.items):
            if parse_qs(urlparse(url).query).get('mode') == [mode]:
                return self.open(clicked(url))
        self.fail('nothing listed opens ' + mode)

    def test_the_main_menu_adds_nothing(self):
        self.assertEqual(self.open(''), '')

    def test_the_path_leads_down_to_a_playlist(self):
        self.open('')
        self.assertEqual(self.follow('menuPlaylists'), 'Playlists')
        self.answer = {'playlistList': [dict(PLAYLIST)], 'nextTokenMap': {'playlist': None}}
        self.assertEqual(self.follow('getPopularPlayLists'), 'Playlists / Playlists - Popular')
        self.answer = NOTHING
        self.assertEqual(self.follow('lookup'), 'Playlists / Playlists - Popular / Cool Jazz')

    def test_a_title_with_url_characters_comes_through(self):
        self.open('')
        self.follow('menuPlaylists')
        self.answer = {'playlistList': [dict(PLAYLIST, title='Rock & Roll / 50%')], 'nextTokenMap': {'playlist': None}}
        self.follow('getPopularPlayLists')
        self.answer = NOTHING
        self.assertEqual(self.follow('lookup'), 'Playlists / Playlists - Popular / Rock & Roll / 50%')

    def test_a_recent_search_shows_what_was_searched_for(self):
        Kodi.settings['search1PlayLists'] = 'jazz'
        self.open('')
        self.follow('menuPlaylists')
        self.assertEqual(self.follow('search1PlayLists'), 'Playlists / Last Search -1 : jazz')

    def test_the_path_leads_into_a_recommendation(self):
        self.answer = {'blocks': [{'__type': 'Shoveler', 'title': 'Top Playlists', 'blocks': []}]}
        self.open('')
        self.assertEqual(self.follow('getNewRecom'), 'Recommendations')
        self.assertEqual(self.follow('getNewRecomDetails'), 'Recommendations / Top Playlists')

    def test_the_next_page_stays_in_the_folder(self):
        invoke(urlencode({'mode': 'getArtistDetails', 'asin': 'B001RJ93XS',
                          'crumbs': json.dumps(['Artist - Search', 'Alphaville'])}))
        next_page = AMitem().setPaginator('next-page-token', None, 'B001RJ93XS')[0]
        self.assertEqual(self.open(clicked(next_page)), 'Artist - Search / Alphaville')

    def test_a_song_carries_no_path(self):
        Kodi.settings['search1Songs'] = 'jazz'
        self.open('')
        self.follow('menuSongs')
        self.answer = {'results': [{'hits': [{'document': dict(TRACK)}], 'nextPage': None}]}
        self.follow('search1Songs')
        songs = [url for url, li, folder in Kodi.items if not folder]
        self.assertEqual(len(songs), 1)
        self.assertNotIn('crumbs', parse_qs(urlparse(songs[0]).query))


if __name__ == '__main__':
    unittest.main()
