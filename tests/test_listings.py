"""What ends up in a listing, and how it is marked."""

import json
import unittest
from urllib.parse import parse_qs, urlparse

from .support import AddonTest, Kodi, Response, clicked, invoke, signed_in, text
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

    def test_an_old_setting_that_turned_the_colours_off_is_ignored(self):
        Kodi.settings['showcolentr'] = 'false'
        self.assertEqual(self.marked(PURCHASED_TRACK, 'PRIME'), (True, GOLD))

    def searched_songs(self):
        Kodi.settings['search1Songs'] = 'jazz'
        invoke('mode=search1Songs')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess(), 'PRIME'))
        self.patch(AMcall, 'amzCall', return_value={'results': [{
            'hits': [{'document': dict(CATALOGUE_TRACK)}, {'document': dict(UNAVAILABLE_TRACK)}], 'nextPage': None}]})
        AmazonMedia().reqDispatch()
        return [li.label for url, li, folder in Kodi.items]

    def test_a_prime_account_finds_the_catalogue_in_a_song_search(self):
        self.assertIn('Big in Japan', self.searched_songs())

    def test_unplayable_songs_are_hidden_by_default(self):
        self.assertEqual(self.searched_songs(), ['Big in Japan'])

    def test_unplayable_songs_are_listed_when_the_setting_is_off(self):
        Kodi.settings['hideUnplayableSongs'] = 'false'
        self.assertEqual(self.searched_songs(), ['Big in Japan', RED % 'An Unavailable Song'])


class EmptyFolders(AddonTest):
    # Amazon lists them, but a lookup of one comes back without a single title.
    def listed(self, query, answer):
        Kodi.items.clear()
        invoke(query)
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess(), 'PRIME'))
        self.patch(AMcall, 'amzCall', return_value=answer)
        AmazonMedia().reqDispatch()
        return [li.label for url, li, folder in Kodi.items]

    def recommended_playlists(self):
        playlists = [dict(CATALOGUE_TRACK, title='A Playlist'), dict(UNAVAILABLE_TRACK, title='An Empty Playlist')]
        return self.listed('mode=getRecomPlayLists', {'recommendations': [
            {'recommendationType': 'PLAYLIST', 'playlists': playlists, 'nextResultsToken': None}]})

    def searched_albums(self):
        Kodi.settings['search1Albums'] = 'jazz'
        albums = [dict(CATALOGUE_TRACK, title='An Album'), dict(UNAVAILABLE_TRACK, title='An Empty Album')]
        return self.listed('mode=search1Albums', {'results': [
            {'hits': [{'document': album} for album in albums], 'nextPage': None}]})

    def test_an_empty_folder_is_left_out_whatever_the_setting(self):
        for hide in ('true', 'false'):
            Kodi.settings['hideUnplayableSongs'] = hide
            with self.subTest(hideUnplayableSongs=hide):
                self.assertEqual(self.recommended_playlists(), ['A Playlist'])
                self.assertEqual(self.searched_albums(), ['An Album'])


class RecentlyAdded(AddonTest):
    def told(self, tracks):
        invoke('mode=getRecentlyAddedSongs')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', side_effect=lambda api, *args:
                   {'resultList': tracks} if api == 'APIV3getTracks' else {'trackList': []})
        AmazonMedia().reqDispatch()
        return Kodi.notifications

    def test_an_empty_list_says_nothing_was_added_in_the_last_90_days(self):
        self.assertEqual(self.told([]), [{'heading': 'Information', 'message': text(30079), 'icon': 'info'}])

    def test_a_list_with_songs_says_nothing(self):
        self.assertEqual(self.told([{'metadata': dict(PURCHASED_TRACK)}]), [])


class Charts(AddonTest):
    def listed(self, query, answer):
        invoke(query)
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', return_value=answer)
        AmazonMedia().reqDispatch()
        return [(li.label, parse_qs(urlparse(url).query)['mode'][0], folder) for url, li, folder in Kodi.items]

    def test_a_charted_album_opens(self):
        album = dict(CATALOGUE_TRACK, title='An Album', artist={'name': 'An Artist'})
        self.assertEqual(self.listed('mode=getPopularAlbums', {'albumList': [album], 'nextTokenMap': {'album': None}}),
                         [('An Album', 'lookup', True)])

    def test_a_charted_song_plays(self):
        self.assertEqual(self.listed('mode=getNewSongs', {'trackList': [dict(CATALOGUE_TRACK)], 'nextTokenMap': {'track': None}}),
                         [('Big in Japan', 'getTrack', False)])


class LibraryArtists(AddonTest):
    def test_an_artist_of_the_library_opens_its_songs_in_the_library(self):
        # The library lists an artist without saying whether anything of it can be streamed.
        invoke('mode=getLibraryArtists')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', return_value={'resultList': [{'metadata': {
            'artistName': 'An Artist', 'artistAsin': 'B0ANARTIST', 'objectId': 'object-id'}, 'numTracks': 3}]})
        AmazonMedia().reqDispatch()
        url, li, folder = Kodi.items[0]
        query = parse_qs(clicked(url))
        self.assertEqual((li.label, folder, query['mode'], query['artist']),
                         ('An Artist  (3 Hits)', True, ['getLibraryArtistSongs'], ['An Artist']))


class Artwork(AddonTest):
    def test_a_listed_album_shows_its_cover_as_background_too(self):
        cover = 'https://m.media-amazon.com/images/I/cover.jpg'
        Kodi.settings['search1Albums'] = 'jazz'
        invoke('mode=search1Albums')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', return_value={'results': [{'hits': [{'document': dict(
            CATALOGUE_TRACK, title='An Album', artFull={'URL': cover})}], 'nextPage': None}]})
        AmazonMedia().reqDispatch()
        art = Kodi.items[0][1].art
        self.assertEqual((art.get('thumb'), art.get('fanart')), (cover, cover))


class AlbumInfo(AddonTest):
    def test_a_listed_album_tells_its_artist_and_year(self):
        album = {'asin': 'B0ANALBUM1', 'albumName': 'An Album', 'artistName': 'An Artist',
                 'originalReleaseDate': 1190368800000, 'totalNumberOfTracks': 5, 'isMusicSubscription': True}
        invoke('mode=getRecomAlbums')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', return_value={'recommendations': [
            {'recommendationType': 'ALBUM', 'albums': [album], 'nextResultsToken': None}]})
        AmazonMedia().reqDispatch()
        info = Kodi.items[0][1].info
        self.assertEqual({key: info.get(key) for key in ('mediatype', 'artist', 'year')},
                         {'mediatype': 'album', 'artist': 'An Artist', 'year': 2007})


class Amazon:
    """Answers the add-on's requests the way the Amazon Music API does."""

    def __init__(self, in_catalogue=True):
        self.requests = []
        self.in_catalogue = in_catalogue

    def post(self, url, headers, data, cookies=None):
        operation = headers['X-Amz-Target'].rsplit('.', 1)[-1]
        self.requests.append((url, operation, json.loads(data)))
        if operation == 'getAlbums':
            # Cirrus v3 knows an album by albumAsin only, and does not say whether it was bought.
            return Response({'resultList': [{'metadata': {
                'albumAsin': 'B0LIBALBUM', 'albumName': 'A Library Album', 'sortAlbumName': 'library album',
                'albumArtistName': 'An Artist', 'objectId': 'object-id'}}], 'totalCount': 1})
        if operation == 'lookup':
            # The catalogue knows nothing of a purchase, and nothing of an album it does not carry.
            albums = [{'asin': 'B0LIBALBUM', 'title': 'A Library Album', 'isPrime': False,
                       'isMusicSubscription': True}] if self.in_catalogue else []
            return Response({'albumList': albums})
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

    def listed_album(self, query):
        invoke(query)
        AmazonMedia().reqDispatch()
        url, li, folder = Kodi.items[0]
        return li.label, parse_qs(urlparse(url).query)['mode'][0]

    def test_a_purchased_album_is_gold_and_opens(self):
        self.assertEqual(self.listed_album('mode=getPurAlbums'), (GOLD % 'A Library Album', 'lookup'))

    def test_a_library_album_the_catalogue_does_not_carry_is_gold_and_opens(self):
        self.amazon.in_catalogue = False
        self.assertEqual(self.listed_album('mode=getAllAlbums'), (GOLD % 'A Library Album', 'lookup'))

    def test_an_album_added_from_the_catalogue_is_not_taken_for_a_purchase(self):
        self.assertEqual(self.listed_album('mode=getAllAlbums'), (PLAIN % 'A Library Album', 'lookup'))


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
