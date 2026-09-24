#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math, random, requests, json, datetime
from resources.lib.tools import AMtools
from resources.lib.api import AMapi

class AMcall( AMtools ):
#class AMcall( ):
    """
    Common class for the Amazon API calls
    """
    LIBRARY_ALBUM_ATTRIBUTES = ['albumName', 'albumArtistName', 'albumAsin', 'objectId',
                                'albumCoverImageFull', 'sortAlbumName', 'albumReleaseDate', 'primaryGenre']
    LIBRARY_TRACK_ATTRIBUTES = ['trackNum', 'discNum', 'duration', 'albumReleaseDate', 'primaryGenre',
                                'albumName', 'artistName', 'title', 'asin', 'objectId', 'albumAsin',
                                'artistAsin', 'purchased', 'status', 'primeStatus', 'albumCoverImageFull']

    def libraryData( self, attributes, filters, sort, order='ASC', paged=False ):
        """
        Request body of a Cirrus v3 library call
        :param array attributes:    item fields to return
        :param array filters:       filterList entries
        :param str sort:            attribute to sort by
        :param str order:           ASC or DESC
        :param bool paged:          pass on the page token of the current request
        """
        data = {
            'filterList':       filters,
            'attributeList':    attributes,
            'sortOrder':        {'sort': sort, 'order': order},
            'maxResults':       self.G['maxResults'],
            'musicTerritory':   self.credentials.MUSICTERRITORY,
            'customerId':       self.credentials.CUSTOMERID,
            'deviceId':         self.credentials.DEVICEID,
            'deviceType':       self.credentials.DEVICETYPE
        }
        token = self.G['addonArgs'].get('token', [None])[0] if paged else None
        if token:
            data['nextToken'] = token
        return json.dumps(data)

    @staticmethod
    def libraryFilter( name, value, comparison='EQUALS' ):
        return {'attributeName': name, 'comparisonType': comparison, 'attributeValue': value}

    def getMaestroID( self ):
        """
        Calculate random Player ID
        """
        a = str(
            float.hex(
                float(
                    math.floor(16 * (1 + random.random()))
                )
            )
        )[4:5]
        uid = '{}-{}-dmcp-{}-{}{}'.format(
            self.doCalc(),
            self.doCalc(),
            self.doCalc(),
            self.doCalc(),
            a
        )
        return 'Maestro/1.0 WebCP/1.0.202638.0 ({})'.format( uid )
    
    @staticmethod
    def doCalc():
        """
        Calculate random ID
        """
        return str(
            float.hex(
                float(
                    math.floor(65536 * (1 + random.random()))
                )
            )
        )[4:8]

    def amzCall( self, amzUrl, mode, referer=None, asin=None, mediatype=None ):
        """
        Main function for the Amazon Call
        :param str amzUrl:  Endpoint ID
        :param str mode:    Request Addon Data ID
        :param str referer: no longer in use
        :param str asin:    Playlist-, Albums-, Song-, Artist-ID
        :param str/array mediatype: content depends on the caller function
        """
        self.credentials = self.load()

        amPath = AMapi.getAPI( amzUrl )

        url  = '{}/{}/api/{}'.format(
            self.musicURL.format( self.credentials.USERTLD ),
            self.credentials.REGION,
            amPath['path']
        )

        head = self.prepReqHeader(amPath['target'])
        data = self.prepReqData( mode, asin, mediatype )

        resp = requests.post( url=url, headers=head, data=data, cookies=self.credentials.COOKIE )
        self.saveCookie( self.credentials.COOKIE )

        if self.G['logging']:
            self.log('url: ' + url)
            self.log('reason: ' + resp.reason + ', code: ' + str(resp.status_code))
            self.log(resp.text)

        if mode == 'getTrackDash':
            return resp
        else:
            return resp.json()

    def prepReqData( self, mode, asin=None, mediatype=None ):
        """
        Provide request data structure for Amazon API calls

        rankType:           newly-added, popularity-rank, top-sellers, newly-released
        requestedContent:   FULL_CATALOG, KATANA, MUSIC_SUBSCRIPTION, PRIME_UPSELL_MS, ALL_STREAMABLE, PRIME
        features:           fullAlbumDetails, playlistLibraryAvailability, childParentOwnership, trackLibraryAvailability,
                            hasLyrics, expandTracklist, ownership, popularity, albumArtist, collectionLibraryAvailability
        types:              artist, track, album, similarArtist, playlist, station

        :param str mode:            Request Addon Data ID
        :param str asin:            Playlist-, Albums-, Song-, Artist-ID
        :param str/array mediatype: content depends on the caller function
        """
        #data = json.dumps(data)
        #data = json.JSONEncoder().encode(data)
        token = self.G['addonArgs'].get('token', [''])
        if   mode == 'searchItems':
            if self.G['addonArgs'].get('token', [None])[0] == None:
                prop = 'maxResults'
                val = self.G['maxResults']
            else:
                prop = 'pageToken'
                val = self.G['addonArgs'].get('token', [None])[0]

            data = {
                'customerIdentity': {
                    'deviceId': self.credentials.DEVICEID,
                    'deviceType': self.credentials.DEVICETYPE,
                    'sessionId': '',
                    'customerId': self.credentials.CUSTOMERID
                },
                'features': {
                    'spellCorrection': {
                        'allowCorrection': 'true'
                    }
                },
                'locale': self.credentials.LOCALE,
                'musicTerritory': self.credentials.MUSICTERRITORY,
                'query': asin,
                'requestContext': 'true',
                'resultSpecs': [{
                    'label': mediatype[0], #'albums',
                    'documentSpecs': [{
                        'type': mediatype[1], #'catalog_album',
                        'fields': [
                            '__DEFAULT',
                            'artOriginal',
                            'artMedium',
                            'artLarge',
                            'artFull',
                            'isMusicSubscription',
                            'primeStatus',
                            'albumName',
                            'albumReleaseDate'
                        ]
                    }],
                    prop : val,
                    # No eligibility restriction: Amazon answers a search that asks for the
                    # PRIME tier with an empty result, whatever is searched for.
                    'contentRestrictions': {
                        'allowedParentalControls': {
                            'hasExplicitLanguage': 'true'
                        }
                    }
                }]
            }
            data = json.JSONEncoder().encode(data)

        elif mode == 'getArtistDetails':
            data  = {
                # Asking for the PRIME tier returns an empty album list for every artist.
                'requestedContent': 'MUSIC_SUBSCRIPTION',
                'asin': asin,
                'types':[{
                    'sortBy':'popularity-rank',
                    'type':'album',
                    'maxCount':     self.G['maxResults'],
                    'nextToken':    self.G['addonArgs'].get('token', [''])[0]
                }],
                'features':[
                    #'expandTracklist',
                    #'collectionLibraryAvailability',
                    'popularity'
                ],
                'deviceId':         self.credentials.DEVICEID,
                'deviceType':       self.credentials.DEVICETYPE,
                'musicTerritory':   self.credentials.MUSICTERRITORY,
                'customerId':       self.credentials.CUSTOMERID
            }
            data = json.dumps(data)

        elif mode == 'getMetaTracks':
            """
            available fields in attributeList:
            ['uploaded', 'composer', 'primaryGenre', 'albumArtistName', 'albumCoverImageFull', 'sortAlbumArtistName', 'purchased', 'fileExtension', 'albumReleaseDate',
            'albumAsin', 'fileName', 'albumCoverImageXL', 'albumContributors', 'songWriter', 'albumCoverImageMedium', 'albumCoverImageLarge', 'orderId', 'assetType',
            'parentalControls', 'marketplace', 'lyricist', 'localFilePath', 'albumRating', 'creationDate', 'bitrate', 'albumArtistAsin', 'performer', 'purchaseDate',
            'sortArtistName', 'albumPrimaryGenre', 'primeStatus', 'discNum', 'status', 'rogueBackfillDate', 'physicalOrderId', 'artistName', 'lastUpdatedDate', 'albumCoverImageTiny',
            'duration', 'audioUpgradeDate', 'albumCoverImageSmall', 'errorCode', 'asin', 'title', 'isMusicSubscription', 'contributors', 'sortTitle', 'objectId', 'albumName',
            'trackNum', 'sortAlbumName', 'publisher', 'fileSize', 'rating', 'md5', 'artistAsin']
            """
            data = {
                'filterList':[
                    {
                        'attributeName':'albumAsin',
                        'comparisonType':'EQUALS',
                        'attributeValue':asin
                    },
                    {
                        'attributeName':'status',
                        'comparisonType':'EQUALS',
                        'attributeValue':'AVAILABLE'
                    }
                ],
                'attributeList':[
                    'trackNum',
                    'discNum',
                    'duration',
                    'albumReleaseDate',
                    'primaryGenre',
                    'albumName',
                    'artistName',
                    'title',
                    'asin',
                    'objectId',

                    'albumAsin',
                    'artistAsin',
                    'purchased',
                    'status',
                    'primeStatus'
                ],
                'sortOrder':{
                    'sort':'albumName',
                    'order':'ASC'
                },
                'maxResults':       self.G['maxResults'],
                'musicTerritory':   self.credentials.MUSICTERRITORY,
                'customerId':       self.credentials.CUSTOMERID,
                'deviceId':         self.credentials.DEVICEID,
                'deviceType':       self.credentials.DEVICETYPE
            }
            data = json.JSONEncoder().encode(data)

        elif mode == 'recentlyaddedsongs':
            data = self.libraryData(
                self.LIBRARY_TRACK_ATTRIBUTES,
                [
                    self.libraryFilter('status', 'AVAILABLE'),
                    self.libraryFilter('creationDate',
                                       str(datetime.date.today() - datetime.timedelta(days=90)),
                                       'GREATER_THAN')
                ],
                'creationDate', 'DESC', paged=True
            )

        elif mode == 'libraryartists':
            data = self.libraryData(
                ['artistName', 'artistAsin', 'objectId'],
                [ self.libraryFilter('status', 'AVAILABLE') ],
                'artistName', paged=True
            )

        elif mode == 'libraryartisttracks':
            data = self.libraryData(
                self.LIBRARY_TRACK_ATTRIBUTES,
                [ self.libraryFilter('status', 'AVAILABLE'), self.libraryFilter('artistName', asin) ],
                'albumName', paged=True
            )

        elif mode == 'followedplaylists':
            data = {
                'optIntoSharedPlaylists': 'true',
                'entryOffset':      0, # todo
                'pageSize':         self.G['maxResults'],
                'deviceId':         self.credentials.DEVICEID,
                'deviceType':       self.credentials.DEVICETYPE,
                'musicTerritory':   self.credentials.MUSICTERRITORY,
                'customerId':       self.credentials.CUSTOMERID
            }
            data = json.dumps(data)

        elif mode == 'getownedplaylists':
            data = {
                'entryOffset':      0, #todo
                'pageSize':         self.G['maxResults'],
                'deviceId':         self.credentials.DEVICEID,
                'deviceType':       self.credentials.DEVICETYPE,
                'musicTerritory':   self.credentials.MUSICTERRITORY,
                'customerId':       self.credentials.CUSTOMERID
            }
            data = json.dumps(data)

        elif mode == 'getplaylistsbyid':
            data = {
                'playlistIds':      [asin],
                'requestedMetadata':['asin','albumName','sortAlbumName','artistName','primeStatus','isMusicSubscription','duration','sortArtistName','sortAlbumArtistName','objectId','title','status','assetType','discNum','trackNum','instantImport','purchased'],
                'deviceId':         self.credentials.DEVICEID,
                'deviceType':       self.credentials.DEVICETYPE,
                'musicTerritory':   self.credentials.MUSICTERRITORY,
                'customerId':       self.credentials.CUSTOMERID
            }
            data = json.dumps(data)

        elif mode in ['playlist', 'album', 'track']:
            data  = {
                'rankType':         mediatype,
                'requestedContent': 'MUSIC_SUBSCRIPTION',
                'features':         ['playlistLibraryAvailability','collectionLibraryAvailability'],
                'types':            [mode],
                'nextTokenMap':     {mode : token[0]},
                'maxCount':         self.G['maxResults'],
                'lang':             self.credentials.LOCALE,
                'deviceId':         self.credentials.DEVICEID,
                'deviceType':       self.credentials.DEVICETYPE,
                'musicTerritory':   self.credentials.MUSICTERRITORY,
                'customerId':       self.credentials.CUSTOMERID
            }
            data = json.dumps(data)

        elif mode == 'recommendations':
            # mediatypes:
            # mp3-prime-browse-carousels_playlistStrategy
            # mp3-prime-browse-carousels_mp3PrimeAlbumsStrategy
            # mp3-prime-browse-carousels_mp3PrimeTracksStrategy
            # mp3-prime-browse-carousels_mp3ArtistStationStrategy
            token = self.G['addonArgs'].get('token', [0])
            data  = {
                'maxResultsPerWidget' : self.G['maxResults'],
                'minResultsPerWidget' : 1,
                'lang' :                self.credentials.LOCALE,
                'requestedContent' :    'PRIME', #self.credentials.ACCESSTYPE,
                'musicTerritory' :      self.credentials.MUSICTERRITORY,
                'deviceId' :            self.credentials.DEVICEID,
                'deviceType' :          self.credentials.DEVICETYPE,
                'customerId' :          self.credentials.CUSTOMERID,
                'widgetIdTokenMap' : { mediatype : int(token[0]) }
            }
            data = json.dumps(data)

        elif mode in ['getLibraryAlbums', 'getLibrarySongs']: # the whole library or only what was bought
            filters = [ self.libraryFilter('status', 'AVAILABLE') ]
            if self.getMode() in ['getPurAlbums', 'getPurSongs']:
                filters.append( self.libraryFilter('purchased', 'true') )
            if mode == 'getLibraryAlbums':
                data = self.libraryData( self.LIBRARY_ALBUM_ATTRIBUTES, filters, 'albumName', paged=True )
            else:
                data = self.libraryData( self.LIBRARY_TRACK_ATTRIBUTES, filters, 'title', paged=True )

        elif mode == 'songs':
            data  = {
                'asins' : [ asin ],
                'features' : [ 'collectionLibraryAvailability','expandTracklist','playlistLibraryAvailability','trackLibraryAvailability','hasLyrics'],
                'requestedContent' : 'MUSIC_SUBSCRIPTION',
                'deviceId' : self.credentials.DEVICEID,
                'deviceType' : self.credentials.DEVICETYPE,
                'musicTerritory' : self.credentials.MUSICTERRITORY,
                'customerId' : self.credentials.CUSTOMERID
            }
            data = json.dumps(data)

        elif mode == 'itemLookup':
            data = {
                'asins': asin, # [asin], is an array!!
                'features': mediatype, # is an array!!
                'requestedContent': 'MUSIC_SUBSCRIPTION',
                'deviceId': self.credentials.DEVICEID,
                'deviceType': self.credentials.DEVICETYPE,
                'musicTerritory': self.credentials.MUSICTERRITORY,
                'customerId': self.credentials.CUSTOMERID
            }
            data = json.JSONEncoder().encode(data)

        elif mode == 'getLibraryAlbumTracks':
            data = self.libraryData(
                self.LIBRARY_TRACK_ATTRIBUTES,
                [
                    self.libraryFilter('status', 'AVAILABLE'),
                    self.libraryFilter('albumAsin', asin)
                ],
                'albumName'
            )

        elif mode == 'getTrackDash':
            mID = self.getMaestroID()
            data = {
                'customerId' :          self.credentials.CUSTOMERID,
                'deviceToken' : {
                    'deviceTypeId' :    self.credentials.DEVICETYPE,
                    'deviceId' :        self.credentials.DEVICEID
                },
                'contentIdList' : [{
                    'identifier' :      asin,
                    'identifierType' :  mediatype
                }],
                'bitrateTypeList' : [ 'HIGH' ],
                'musicDashVersionList' : [ 'V2' ],
                'appInfo' : {
                    'musicAgent': mID # 'Maestro/1.0 WebCP/1.0.202513.0 (9a46-5ad0-dmcp-8d19-ee5c6)'
                },
                'customerInfo' : {
                    'marketplaceId' :   self.credentials.MARKETPLACEID,
                    'customerId' :      self.credentials.CUSTOMERID,
                    'territoryId' :     self.credentials.MUSICTERRITORY,
                    'entitlementList' : [ 'HAWKFIRE' ]
                }
            }
            data = json.dumps(data)

        elif mode == 'getLicenseForPlaybackV2':
            mID = self.getMaestroID()
            # 'b{SSM}' base64NonURLencoded
            # 'B{SSM}' Base64URLencoded
            # 'R{SSM}' Raw format.
            data = {
                'DrmType':'WIDEVINE',
                #'licenseChallenge':'b{SSM}',
                'customerId':self.credentials.CUSTOMERID,
                'deviceToken':{
                    'deviceTypeId':self.credentials.DEVICETYPE,
                    'deviceId':self.credentials.DEVICEID
                },
                'appInfo':{
                    'musicAgent':mID
                },
                'Authorization':self.credentials.ACCESSTOKEN
            }
            if mediatype:
                data['licenseChallenge'] = mediatype
            else:
                data['licenseChallenge'] = 'b{SSM}'
            # '|' separates the fields of the inputstream.adaptive license key, the access token contains one
            data = json.dumps(data).replace('|', '\\u007c')
        return data