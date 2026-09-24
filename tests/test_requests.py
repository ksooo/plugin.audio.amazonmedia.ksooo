"""What the add-on asks Amazon for.

Amazon answers several of these requests with an empty result or an error
when a single field is off, so the tests pin the fields that decided it.
"""

import json
import unittest

from .support import AddonTest, invoke, signed_in
from resources.lib.amzcall import AMcall

# What the Cirrus v3 library API accepted when it was probed; anything else is
# refused with HTTP 400.
LIBRARY_SORT_KEYS = {'albumArtistName', 'genre', 'creationDate', 'purchaseDate',
                     'artistName', 'lastUpdatedDate', 'title', 'albumName'}
LIBRARY_ALBUM_FIELDS = {'albumName', 'albumArtistName', 'albumAsin', 'objectId', 'albumCoverImageFull',
                        'sortAlbumName', 'albumReleaseDate', 'primaryGenre', 'albumPrimaryGenre',
                        'status', 'albumArtistAsin'}


class Requests(AddonTest):
    def body(self, mode, asin=None, mediatype=None):
        call = AMcall()
        signed_in(call.credentials)
        return json.loads(call.prepReqData(mode, asin, mediatype))


class Search(Requests):
    def test_a_search_is_not_restricted_to_a_tier(self):
        # Asked for the PRIME tier, Amazon returns nothing, whatever is searched for.
        for kind in (['playlists', 'catalog_playlist'], ['albums', 'catalog_album'],
                     ['tracks', 'catalog_track'], ['artists', 'catalog_artist']):
            with self.subTest(kind=kind[0]):
                spec = self.body('searchItems', 'jazz', kind)['resultSpecs'][0]
                self.assertNotIn('eligibility', spec['contentRestrictions'])


class Catalogue(Requests):
    def test_artist_albums_are_asked_for_from_the_subscription_catalogue(self):
        # Amazon has no albums left under the PRIME tier, for any artist.
        self.assertEqual(self.body('getArtistDetails', 'B001RJ93XS')['requestedContent'], 'MUSIC_SUBSCRIPTION')

    def test_playlists_are_asked_for_from_the_subscription_catalogue(self):
        invoke('mode=getPopularPlayLists')
        self.assertEqual(self.body('playlist', mediatype='popularity-rank')['requestedContent'], 'MUSIC_SUBSCRIPTION')

    def test_a_chart_asks_for_the_kind_it_lists(self):
        for kind, query in (('playlist', 'mode=getNewPlayLists'), ('album', 'mode=getNewAlbums'), ('track', 'mode=getNewSongs')):
            with self.subTest(kind=kind):
                invoke(query)
                body = self.body(kind, mediatype='newly-released')
                self.assertEqual((body['types'], list(body['nextTokenMap'])), ([kind], [kind]))


class Library(Requests):
    def library_requests(self):
        for mode, query, asin in (('getLibraryAlbums', 'mode=getPurAlbums', None),
                                  ('getLibraryAlbums', 'mode=getAllAlbums', None),
                                  ('getLibrarySongs', 'mode=getPurSongs', None),
                                  ('getLibrarySongs', 'mode=getAllSongs', None),
                                  ('recentlyaddedsongs', 'mode=getRecentlyAddedSongs', None),
                                  ('libraryartists', 'mode=getLibraryArtists', None),
                                  ('libraryartisttracks', 'mode=getLibraryArtistSongs&artist=An%20Artist', 'An Artist'),
                                  ('getLibraryAlbumTracks', 'mode=lookup&asin=B0LIBALBUM', 'B0LIBALBUM')):
            invoke(query)
            yield query, self.body(mode, asin)

    def test_every_library_request_sorts_by_a_key_amazon_accepts(self):
        for query, body in self.library_requests():
            with self.subTest(query=query):
                self.assertIn(body['sortOrder']['sort'], LIBRARY_SORT_KEYS)

    def test_albums_only_ask_for_fields_amazon_returns_for_albums(self):
        invoke('mode=getAllAlbums')
        self.assertLessEqual(set(self.body('getLibraryAlbums')['attributeList']), LIBRARY_ALBUM_FIELDS)

    def filters(self, query, mode):
        invoke(query)
        return {f['attributeName']: f['attributeValue'] for f in self.body(mode)['filterList']}

    def test_purchased_lists_keep_to_what_was_bought(self):
        self.assertEqual(self.filters('mode=getPurAlbums', 'getLibraryAlbums').get('purchased'), 'true')
        self.assertEqual(self.filters('mode=getPurSongs', 'getLibrarySongs').get('purchased'), 'true')

    def test_the_songs_of_a_library_artist_are_asked_for_by_name(self):
        # Amazon refuses to filter the library by artistAsin.
        invoke('mode=getLibraryArtistSongs&artist=An%20Artist')
        filters = {f['attributeName']: f['attributeValue'] for f in self.body('libraryartisttracks', 'An Artist')['filterList']}
        self.assertEqual(filters.get('artistName'), 'An Artist')

    def test_the_whole_library_is_not_limited_to_purchases(self):
        self.assertNotIn('purchased', self.filters('mode=getAllAlbums', 'getLibraryAlbums'))
        self.assertNotIn('purchased', self.filters('mode=getAllSongs', 'getLibrarySongs'))

    def test_the_next_page_is_asked_for_with_the_token_of_the_last_one(self):
        invoke('mode=getAllSongs&token=next-page-token=')
        self.assertEqual(self.body('getLibrarySongs')['nextToken'], 'next-page-token=')

    def test_the_first_page_carries_no_token(self):
        invoke('mode=getAllSongs')
        self.assertNotIn('nextToken', self.body('getLibrarySongs'))


if __name__ == '__main__':
    unittest.main()
