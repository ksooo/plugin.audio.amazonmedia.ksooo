"""What ends up in a listing, and how it is marked."""

import json
import unittest

from .support import AddonTest, Kodi, Response, invoke, signed_in
from resources.lib import amzcall
from resources.lib.access import AMaccess
from resources.lib.amzcall import AMcall
from resources.lib.item import AMitem
from resources.lib.main import AmazonMedia
from resources.lib.tools import AMtools

# How Amazon describes its catalogue today: nothing is marked as Prime any more.
CATALOGUE_TRACK = {'asin': 'B001SG09MY', 'title': 'Big in Japan', 'primeStatus': 'NOT_PRIME',
                   'isMusicSubscription': 'true'}
PURCHASED_TRACK = {'asin': 'B0PURCHASE', 'title': 'A Purchased Song', 'purchased': 'true'}
UNAVAILABLE_TRACK = {'asin': 'B0UNAVAILA', 'title': 'An Unavailable Song', 'primeStatus': 'NOT_PRIME',
                     'isMusicSubscription': 'false'}

GOLD, PLAIN, RED = '[COLOR gold]%s[/COLOR]', '%s', '[COLOR red]%s[/COLOR]'


class Playability(AddonTest):
    def marked(self, track, tier):
        item = AMitem()
        signed_in(item.credentials, tier)
        _, meta = item.setData(dict(track), {'mode': 'getTrack'})
        return meta['isPlayable'], meta['color']

    def test_the_catalogue_is_playable_whatever_the_tier(self):
        for tier in ('PRIME', 'UNLIMITED'):
            with self.subTest(tier=tier):
                self.assertEqual(self.marked(CATALOGUE_TRACK, tier), (True, PLAIN))

    def test_a_purchase_is_playable_and_gold(self):
        self.assertEqual(self.marked(PURCHASED_TRACK, 'PRIME'), (True, GOLD))

    def test_a_title_outside_the_catalogue_is_unplayable_and_red(self):
        self.assertEqual(self.marked(UNAVAILABLE_TRACK, 'PRIME'), (False, RED))

    def test_a_prime_account_sees_the_catalogue_in_a_song_list(self):
        invoke('mode=getRecentlyPlayed')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess(), 'PRIME'))
        self.patch(AMcall, 'amzCall', return_value={'recentActivityMap': {'PLAYED': {
            'recentTrackList': [dict(CATALOGUE_TRACK), dict(UNAVAILABLE_TRACK)], 'nextToken': None}}})
        AmazonMedia().reqDispatch()
        self.assertEqual([li.label for url, li, folder in Kodi.items], ['Big in Japan'])


class Amazon:
    """Answers the add-on's requests the way the Amazon Music API does."""

    def __init__(self):
        self.requests = []

    def post(self, url, headers, data, cookies=None):
        operation = headers['X-Amz-Target'].rsplit('.', 1)[-1]
        self.requests.append((url, operation, json.loads(data)))
        if operation == 'getAlbums':
            # Cirrus v3 knows an album by albumAsin only; it has no asin field.
            return Response({'resultList': [{'metadata': {
                'albumAsin': 'B0LIBALBUM', 'albumName': 'A Library Album', 'sortAlbumName': 'library album',
                'albumArtistName': 'An Artist', 'objectId': 'object-id'}}], 'totalCount': 1})
        if operation == 'lookup':
            return Response({'albumList': [{'asin': 'B0LIBALBUM', 'title': 'A Library Album', 'purchased': True}]})
        raise AssertionError('unexpected request: ' + operation)


class Library(AddonTest):
    def setUp(self):
        super().setUp()
        self.amazon = Amazon()
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(amzcall.requests, 'post', side_effect=self.amazon.post)

    def test_purchased_albums_are_listed(self):
        invoke('mode=getPurAlbums')
        AmazonMedia().reqDispatch()
        self.assertEqual(len(Kodi.items), 1)
        self.assertIn('A Library Album', Kodi.items[0][1].label)

    def test_purchased_albums_come_from_the_v3_library(self):
        invoke('mode=getPurAlbums')
        AmazonMedia().reqDispatch()
        url, operation, _ = self.amazon.requests[0]
        self.assertTrue(url.endswith('/EU/api/cirrus/v3/'), url)
        self.assertEqual(operation, 'getAlbums')

    def test_the_details_of_an_album_are_looked_up_by_its_album_asin(self):
        invoke('mode=getPurAlbums')
        AmazonMedia().reqDispatch()
        lookups = [body for _, operation, body in self.amazon.requests if operation == 'lookup']
        self.assertEqual(lookups[0]['asins'], ['B0LIBALBUM'])


class AlbumOrder(AddonTest):
    def test_the_tracks_of_an_album_from_the_library_play_in_album_order(self):
        # The library API cannot sort by track number and hands the tracks back in any order.
        tracks = [{'metadata': {'asin': 'B%d%02d' % (disc, track), 'discNum': str(disc), 'trackNum': str(track)}}
                  for disc, track in ((1, 10), (2, 1), (1, 2), (1, 1))]
        empty = {'albumList': [], 'artistList': [], 'playlistList': [], 'trackList': []}
        invoke('mode=lookup&asin=B0LIBALBUM')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', side_effect=lambda api, *args: {'resultList': tracks} if api == 'APIV3getTracks' else empty)
        listed = self.patch(AmazonMedia, 'setAddonContent')
        AmazonMedia().reqDispatch()
        _, shown, _ = listed.call_args[0]
        self.assertEqual([(t['metadata']['discNum'], t['metadata']['trackNum']) for t in shown],
                         [('1', '1'), ('1', '2'), ('1', '10'), ('2', '1')])


if __name__ == '__main__':
    unittest.main()
