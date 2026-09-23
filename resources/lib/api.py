#!/usr/bin/env python
# -*- coding: utf-8 -*-

class AMapi():
    """
    Amazon Media API definitions \n
    amzUrl      = AmazonBaseUrl + region + /api/ + path \n
    amzTarget   = target
    """
    @staticmethod
    def getAPI( amapi ):
        """
        Provides Amazon URL and Service endpoint
        :param str amapi: the requested API
        """
        if  amapi == 'APIgetBrowseRecommendations':
            s = {   'path':   'muse/legacy/getBrowseRecommendations',
                    'target': 'com.amazon.musicensembleservice.MusicEnsembleService.getBrowseRecommendations'
            }
        elif amapi == 'APIlookup':
            s = {   'path':   'muse/legacy/lookup',
                    'target': 'com.amazon.musicensembleservice.MusicEnsembleService.lookup'
            }
        elif amapi == 'APIgetStationSections':
            s = {   'path':   'muse/stations/getStationSections',
                    'target': 'com.amazon.musicensembleservice.MusicEnsembleService.getStationSectionsGet',
                    'method': 'GET'
            }
        elif amapi == 'APIartistDetailsMetadata':
            s = {   'path':   'muse/artistDetailsMetadata',
                    'target': 'com.amazon.musicensembleservice.MusicEnsembleService.artistDetailsMetadata'
            }
        elif amapi == 'APIgetTopMusicEntities':  # playlists
            s = {   'path':   'muse/getTopMusicEntities',
                    'target': 'com.amazon.musicensembleservice.MusicEnsembleService.getTopMusicEntities'
            }
        elif amapi == 'APIgetHome':
            s = {   'path':   'muse/getHome',
                    'target': 'com.amazon.musicensembleservice.MusicEnsembleService.getHome'
            }

        elif amapi == 'APIcreateQueue': # genres
            s = {   'path':   'mpqs/voiceenabled/createQueue',
                    'target': 'com.amazon.musicplayqueueservice.model.client.external.voiceenabled.MusicPlayQueueServiceExternalVoiceEnabledClient.createQueue'
            }
        elif amapi == 'APIQueueGetNextTracks': # genres
            s = {   'path':   'mpqs/voiceenabled/getNextTracks',
                    'target': 'com.amazon.musicplayqueueservice.model.client.external.voiceenabled.MusicPlayQueueServiceExternalVoiceEnabledClient.getNextTracks'
            }
        # get streaming url
        elif amapi == 'APIstreamDash': # ASIN (musicDashVersionList: ["V1", "V2"])
            s = {   'path':   'dmls/',
                    'target': 'com.amazon.digitalmusiclocator.DigitalMusicLocatorServiceExternal.getDashManifestsV2'
            }
        elif amapi == 'APILicenseForPlaybackV2':
            s = {   'path':   'dmls/',
                    'target': 'com.amazon.digitalmusiclocator.DigitalMusicLocatorServiceExternal.getLicenseForPlaybackV2'
            }
        # search
        elif amapi == 'APIsearch':
            s = {   'path':   'textsearch/search/v1_1/',
                    'target': 'com.amazon.tenzing.textsearch.v1_1.TenzingTextSearchServiceExternalV1_1.search'
            }
        elif amapi == 'APIV3getTracks':
            s = {   'path':   'cirrus/v3/',
                    'target': 'com.amazon.cirrus.libraryservice.v3.CirrusLibraryServiceExternalV3.getTracks',
                    'operation': 'getTracks'
            }
        elif amapi == 'APIV3getAlbums':
            s = {   'path':   'cirrus/v3/',
                    'target': 'com.amazon.cirrus.libraryservice.v3.CirrusLibraryServiceExternalV3.getAlbums'
            }
        elif amapi == 'APIgetPlaylistsByIdV2':
            s = {   'path':   'playlists/',
                    'target': 'com.amazon.musicplaylist.model.MusicPlaylistService.getPlaylistsByIdV2'
            }
        elif amapi == 'APIgetFollowedPlaylistsInLibrary':
            s = {   'path':   'playlists/',
                    'target': 'com.amazon.musicplaylist.model.MusicPlaylistService.getFollowedPlaylistsInLibrary'
            }
        elif amapi == 'APIgetOwnedPlaylistsInLibrary':
            s = {   'path':   'playlists/',
                    'target': 'com.amazon.musicplaylist.model.MusicPlaylistService.getOwnedPlaylistsInLibrary'
            }
        # TODO NEW ownedPlaylist selection
        # https://eu.web.skill.music.a2z.com/api/showLibraryPlaylists
        # self.APIshowLibraryPlaylists = {
        #     'path':   'https://eu.web.skill.music.a2z.com/api/showLibraryPlaylists',
        #     'target': ''
        # }
        elif amapi == 'APIGetRecentTrackActivity':
            s = {   'path':   'nimbly/',
                    'target': 'com.amazon.nimblymusicservice.NimblyMusicService.GetRecentTrackActivity'
            }
        else:
            raise Exception("No API provided!")

        return s
