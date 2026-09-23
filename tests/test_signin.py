"""Signing in: the domain an account ends up on, and approval on another device."""

import os
import unittest

import mechanicalsoup

from .support import AddonTest, Kodi
from resources.lib.logon import AMlogon

# The approval page as Amazon serves it, cut down to what the add-on reads.
APPROVAL_PAGE = '''<html><body><div class="a-section chimera-body-container">
<div class="a-section a-spacing-medium"><span class="a-size-base-plus transaction-approval-word-break a-text-bold">
Genehmige zu deiner Sicherheit die Benachrichtigung, die an folgende Adresse gesendet wurde:</span></div>
<div id="channelDetailsWithImprovedLayout" class="a-section">
<div class="a-section a-spacing-extra-large">
<div class="a-row a-spacing-small"><div class="a-column a-span4"><span class="a-color-tertiary">Geltungsbereich</span></div>
<div class="a-column a-span8 a-span-last">          Amazon Music, Smartphone
</div></div>
</div></div>
<form id="pollingForm" method="get" action="/ap/cvf/approval/poll"><input type="hidden" name="arb" value="x"/></form>
</div></body></html>'''

# What submitting the polling form returns while the user has not answered yet.
PENDING = '<html><body><input type="hidden" name="transactionApprovalStatus" value="TransactionPending"/></body></html>'

# What the approval page turns into once the user has approved.
SIGNED_IN = '<html><body>Amazon Music</body></html>'


def app_config(territory):
    return {'accessToken': 'token', 'csrf': {'token': 'csrf', 'ts': '1', 'rnd': '2'},
            'deviceId': 'device-id', 'customerId': 'customer-id', 'marketplaceId': 'marketplace-id',
            'deviceType': 'device-type', 'musicTerritory': territory, 'displayLanguage': 'en_GB',
            'siteRegion': 'EU', 'tier': 'PRIME'}


class Domain(AddonTest):
    def test_a_uk_account_stays_on_the_uk_domain(self):
        logon = AMlogon()
        logon._appConfig(app_config('GB'))
        self.assertEqual(logon.credentials.USERTLD, 'co.uk')

    def test_a_territory_that_is_its_own_domain_is_kept(self):
        logon = AMlogon()
        logon._appConfig(app_config('FR'))
        self.assertEqual(logon.credentials.USERTLD, 'fr')


class Browser:
    """The part of mechanicalsoup the approval step uses, fed with fixed pages."""

    url = 'https://www.amazon.de/ap/cvf/approval?openid.return_to=https%3A%2F%2Fmusic.amazon.de%2F'

    def __init__(self, logon, polls):
        self.logon = logon
        self.polls = list(polls)

    def select_form(self, selector):
        if 'pollingForm' not in self.logon._content:
            raise mechanicalsoup.LinkNotFoundError()

    def open_next(self, url):
        self.logon._content = self.polls.pop(0)


class Approval(AddonTest):
    def signing_in(self, polls):
        logon = AMlogon()
        logon._br = Browser(logon, polls)
        logon._content = APPROVAL_PAGE
        self.patch(logon, '_open', side_effect=logon._br.open_next)
        self.patch(logon, '_getLogonResponse', side_effect=lambda: setattr(logon, '_content', PENDING))
        return logon

    def test_the_prompt_says_where_the_notification_went(self):
        logon = AMlogon()
        message = logon._approvalMessage(logon._parseHTML(APPROVAL_PAGE))
        self.assertEqual(message.split(os.linesep), [
            'Genehmige zu deiner Sicherheit die Benachrichtigung, die an folgende Adresse gesendet wurde:',
            'Geltungsbereich: Amazon Music, Smartphone'])

    def test_the_waiting_dialog_shows_the_whole_prompt(self):
        logon = self.signing_in([SIGNED_IN])
        logon._checkMFA()
        self.assertIn('Geltungsbereich: Amazon Music, Smartphone', Kodi.progress[0])

    def test_the_sign_in_goes_on_once_the_request_is_approved(self):
        logon = self.signing_in([APPROVAL_PAGE, SIGNED_IN])
        self.assertTrue(logon._checkMFA())
        self.assertEqual(logon._content, SIGNED_IN)


if __name__ == '__main__':
    unittest.main()
