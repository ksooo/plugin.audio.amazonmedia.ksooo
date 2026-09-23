#!/usr/bin/env python
# -*- coding: utf-8 -*-
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingTCPServer
import os
from urllib.parse import urlparse, parse_qsl

import xbmc, xbmcvfs, xbmcaddon

class ProxyHTTPD(BaseHTTPRequestHandler):
    # HTTP/1.0, so the client closes the connection after the manifest it asked
    # for. Kept open, the handler thread would sit in a read until Kodi exits.
    protocol_version = 'HTTP/1.0'
    server_version = 'AmazonMadia/0.1'

    def log_message(self, *args):
        """Disable the BaseHTTPServer Log"""
        pass

    def log(self, msg, level=xbmc.LOGINFO):
        log_message = '[{}] {}'.format('AM Proxy', msg)
        xbmc.log(log_message, level)

    def _ParseBaseRequest(self, method):
        """Return path, headers and post data commonly required by all methods"""
        # self.log('_ParseBaseRequest')
        # path = py2_decode(urlparse(self.path).path[1:])  # Get URI without the trailing slash
        path = urlparse(self.path).path[1:]  # Get URI without the trailing slash
        path = path.split('/')  # license/<asin>/<ATV endpoint>
        # self.log('[PS] Requested {} path {}'.format(method, path))
        # Retrieve headers and data
        headers = {k: self.headers[k] for k in self.headers if k not in ['host', 'content-length']}
        data_length = self.headers.get('content-length')
        data = {k: v for k, v in parse_qsl(self.rfile.read(int(data_length)))} if data_length else None
        return (path, headers, data)

    def do_GET(self):
        """Respond to GET requests"""
        # self.log('do get')
        path, head, data = self._ParseBaseRequest('GET')
        if path is None:
            return
        # self.log(path[0])
        # self.log(head)

        if (path[0] == 'mpd') and (2 == len(path)):
            #self._AlterMPD(unquote(path[1]), head, data)
            
            _addonUDatFo = xbmcvfs.translatePath('special://profile/addon_data/{}'.format(xbmcaddon.Addon().getAddonInfo('id')))
            song = '{}{}song.mpd'.format(_addonUDatFo,os.sep)
            # song = xbmcvfs.translatePath(song).decode('utf-8')
            song = xbmcvfs.File(song)
            size = song.size()
            # self.log('Song size: ' + str(size))

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Content-Length', str(size))
            self.end_headers()

            self.wfile.write(song.readBytes())
            song.close()
            #self._EndChunkedTransfer(gzstream)

        else:
            self.log('[PS] Invalid request received')
            self.send_error(501, 'Invalid request')

class ProxyTCPD(ThreadingTCPServer):
    # As ThreadingHTTPServer does it: server_close() waits for every handler
    # thread otherwise, which holds up the shutdown of Kodi.
    daemon_threads = True

    def __init__(self):
        """ Initialisation of the Proxy TCP server """
        from socket import socket, AF_INET, SOCK_STREAM
        sock = socket(AF_INET, SOCK_STREAM)

        while True:
            try:
                sock.bind(('127.0.0.1', 0))
                _, port = sock.getsockname()
                sock.close()
                ThreadingTCPServer.__init__(self, ('127.0.0.1', port), ProxyHTTPD)
                self.port = port  # Save the current binded port
                break
            except:
                pass
