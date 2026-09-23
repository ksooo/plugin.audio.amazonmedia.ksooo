"""What the user is told when Amazon hands out no stream."""

import unittest

from .support import AddonTest, Kodi, Response, invoke, signed_in, text
from resources.lib.access import AMaccess
from resources.lib.amzcall import AMcall
from resources.lib.play import AMplay
from resources.lib.tools import AMtools


class Refused(AddonTest):
    def play(self, status):
        invoke('mode=getTrack&asin=B0PURCHASE')
        self.patch(AMtools, 'load', lambda tools: signed_in(AMaccess()))
        self.patch(AMcall, 'amzCall', return_value=Response({'contentResponseList': [{
            'contentResponseStatusCode': status, 'contentResponseStatusMessage': '', 'manifest': ''}]}))
        return AMplay().getTrack('B0PURCHASE', None)

    def told(self, reason):
        return [{'heading': 'Error', 'message': text(30073) + ' ' + text(reason), 'icon': 'error'}]

    def test_a_title_amazon_does_not_stream_says_so(self):
        # Purchases that are not part of the streaming catalogue are refused this way.
        self.assertFalse(self.play('CONTENT_NOT_ELIGIBLE'))
        self.assertEqual(Kodi.notifications, self.told(30078))

    def test_the_concurrency_limit_is_reported_once(self):
        self.play('MAX_CONCURRENCY_REACHED')
        self.assertEqual(Kodi.notifications, self.told(30075))

    def test_any_other_refusal_says_that_no_stream_was_found(self):
        self.play('BAD_REQUEST')
        self.assertEqual(Kodi.notifications, self.told(30074))


if __name__ == '__main__':
    unittest.main()
