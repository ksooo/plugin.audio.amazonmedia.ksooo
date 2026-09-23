"""How a plugin call ends when something goes wrong, and how it tells the user."""

import os
import re
import unittest

from .support import AddonTest, HANDLE, Kodi, invoke, signed_in, text, xbmc
from resources.lib.access import AMaccess
from resources.lib.amzcall import AMcall
from resources.lib.logon import AMlogon
from resources.lib.main import AmazonMedia
from resources.lib.tools import AMtools


class FailedRequest(AddonTest):
    def setUp(self):
        super().setUp()
        self.stored = [os.path.join(Kodi.profile, name) for name in ('cookie', 'data.obj')]
        for path in self.stored:
            open(path, 'w').close()
        invoke('mode=getRecentlyPlayed')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', side_effect=ValueError('Amazon answered 500'))
        self.logon = self.patch(AMlogon, 'amazonLogon')
        AmazonMedia().reqDispatch()

    def test_the_stored_sign_in_survives(self):
        self.assertEqual([os.path.exists(path) for path in self.stored], [True, True])

    def test_the_user_is_not_asked_to_sign_in_again(self):
        self.logon.assert_not_called()

    def test_the_failure_is_shown_as_an_error(self):
        self.assertEqual(Kodi.notifications, [{'heading': 'Error', 'message': text(30077), 'icon': 'error'}])

    def test_the_listing_is_ended_as_failed(self):
        self.assertEqual(Kodi.directories, [(HANDLE, False)])

    def test_the_cause_ends_up_in_the_log(self):
        errors = [message for level, message in Kodi.log if level == xbmc.LOGERROR]
        self.assertTrue(any('Amazon answered 500' in message for message in errors))


class Information(AddonTest):
    def titles(self):
        return [re.match(r'Notification\("([^"]*)"', command).group(1) for command in Kodi.builtins]

    def test_the_title_of_an_information_carries_no_colon(self):
        for mode in ('resetCredentials', 'resetAddon'):
            with self.subTest(mode=mode):
                del Kodi.builtins[:]
                invoke('mode=' + mode)
                AmazonMedia().reqDispatch()
                self.assertEqual(self.titles(), ['Information'])


if __name__ == '__main__':
    unittest.main()
