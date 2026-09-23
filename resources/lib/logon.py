#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, mechanicalsoup, requests
import urllib.parse as urlparse
from bs4 import BeautifulSoup
from resources.lib.tools import AMtools

import xbmc, xbmcgui

class AMlogon( AMtools ):
    """
    Connection class provides user login.
    """
    LOCALES = {'de': 'de_DE', 'fr': 'fr_FR', 'co.uk': 'en_GB', 'it': 'it_IT', 'es': 'es_ES'}
    ASSOC_HANDLES = {'co.uk': 'amzn_webamp_uk'}

    # markers of the pages Amazon may show between password and web player
    MFA_KEYWORDS = ['auth-mfa-form', 'name="claimspicker"', 'auth-select-device-form', 'verification-code-form',
                    'cvf-widget-form', 'pollingForm', 'resend-approval-form', 'validateCaptcha',
                    'auth-captcha-image-container']

    def _getLocale( self ):
        return self.credentials.LOCALE or self.LOCALES.get(self.credentials.USERTLD, 'en_US')

    def _acceptLanguage( self ):
        locale = self._getLocale()
        return '{},{};q=0.8,en;q=0.6'.format(locale.replace('_', '-'), locale.split('_')[0])

    def _getCredentials( self ):
        """
        User dialog for E-Mail and Password
        """
        if not self.credentials.USEREMAIL or not self.credentials.USERPASSWORD:
            if not self.credentials.USEREMAIL:
                user = self.getUserInput( self.getTranslation(30030), '', hidden=False, uni=False ) # get Email
                if user:
                    self.credentials.USEREMAIL = user
            else:
                user = True
            if user and not self.credentials.USERPASSWORD:
                pw = self.getUserInput( self.getTranslation(30031), '', hidden=True, uni=False ) # get Password
                if pw:
                    self.credentials.USERPASSWORD = pw
                    return True
                else:
                    return False
            else:
                return False
        return True

    @staticmethod
    def _parseHTML( resp ):
        """
        Make the request more readable
        """
        resp = re.sub(r'(?i)(<!doctype \w+).*>', r'\1>', resp)
        return BeautifulSoup(resp, 'html.parser')

    def _prepBrowser( self ):
        """
        Setup the virtual brower with header information for logon
        """
        self._br = mechanicalsoup.StatefulBrowser(soup_config={'features': 'html.parser'})
        self._br.set_cookiejar(self.credentials.COOKIE)
        self._br.session.headers.update({
            'Accept':           'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language':  self._acceptLanguage(),
            'User-Agent':       self.userAgent,
            'Upgrade-Insecure-Requests': '1'
        })

    def amazonLogon( self ):
        """
        Entry point for logon procedure
        """
        if not self._getCredentials():  return False
        self._prepBrowser()
        tld = self.credentials.USERTLD
        params = {
            "openid.pape.max_auth_age" : "3600",
            "openid.return_to" : 'https://music.amazon.{}/?referer=https%3A%2F%2Fmusic.amazon.{}%2F'.format(tld, tld),
            "openid.identity" : "http://specs.openid.net/auth/2.0/identifier_select",
            "openid.assoc_handle" : self.ASSOC_HANDLES.get(tld, 'amzn_webamp_{}'.format(tld)),
            "openid.mode" : "checkid_setup",
            "language" : self._getLocale(),
            "openid.claimed_id" : "http://specs.openid.net/auth/2.0/identifier_select",
            "pageId" : "login",
            "openid.ns" : "http://specs.openid.net/auth/2.0"
        }
        amzURL = 'https://www.amazon.{}/ap/signin?{}'.format(tld, urlparse.urlencode(params))

        self._open(amzURL)
        self._br.select_form('form[name="signIn"]')
        if self._hasControl("email"):
            self._br["email"] = self.credentials.USEREMAIL
        if self._hasControl("password"):
            self._br["password"] = self.credentials.USERPASSWORD
        self._getLogonResponse()
        if 'SIGNIN_PWD_COLLECT' in self._content:
            # two step sign-in, the password is asked on a second page
            self._dumpPage('signin-email')
            self._br.select_form('form[name="signIn"]')
            self._br["password"] = self.credentials.USERPASSWORD
            self._getLogonResponse()
        self._dumpPage('signin')

        if not self._checkMFA():    return False
        if not self._checkConfig():
            xbmcgui.Dialog().ok(self.getInfo('name'), self._errorMessage())
            return False

        #self.credentials.USEREMAIL      = None # do not store user mail
        self.credentials.USERPASSWORD   = None # do not store user password
        self.save( self.credentials )
        return self.credentials

    def _getLogonResponse( self ):
        """
        Reusable submit function, stores the response in class variable
        """
        self._content = self._br.submit_selected().text

    def _open( self, url ):
        self._content = self._br.open(url).text

    def _dumpPage( self, name ):
        """
        With addon logging enabled, keep the current page in addon_data for troubleshooting
        """
        if not self.G['logging']:
            return
        forms = [f.get('id') or f.get('name') or f.get('class') for f in self._parseHTML(self._content).find_all('form')]
        self.log('{}: url {} forms {}'.format(name, self._br.url, forms))
        path = os.path.join(self.G['addonUDatFo'], 'logon-{}.html'.format(name))
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._content.replace(self.credentials.USEREMAIL or '', '**@**'))

    def _hasControl( self, name ):
        return self._br.form.form.find(['input', 'select', 'textarea'], attrs={'name': name}) is not None

    def _selectForm( self, selector ):
        try:
            self._br.select_form(selector)
            return True
        except mechanicalsoup.LinkNotFoundError:
            self.log('Form not found: {}'.format(selector))
            return False

    def _setControl( self, name, value ):
        try:
            self._br[name] = value
            return True
        except mechanicalsoup.LinkNotFoundError as e:
            self.log('Cannot set control {}: {}'.format(name, e))
            return False

    @staticmethod
    def _text( tag ):
        return re.sub(r'\s+', ' ', tag.get_text(' ', strip=True)) if tag else ''

    def _errorMessage( self ):
        """
        Error text of the last Amazon page, falls back to the generic logon error
        """
        soup = self._parseHTML(self._content)
        for attrs in ({'id': 'auth-error-message-box'}, {'id': 'auth-warning-message-box'},
                      {'id': 'message_error'}, {'class': 'ap_error_page_message'}):
            tag = soup.find('div', attrs=attrs)
            if tag:
                return self._text(tag)
        # pages like the forced password reset only have a heading and a paragraph
        heading = soup.find(['h1', 'h2'])
        if heading:
            return self._text(heading) + os.linesep + self._text(heading.find_next('p'))
        return self.getTranslation(30070)

    def _checkMFA( self ):
        """
        Handle the verification steps Amazon may add after the password was accepted
        """
        for i in range(10):
            if not any(kw in self._content for kw in self.MFA_KEYWORDS):
                return True
            soup = self._parseHTML(self._content)
            self._dumpPage('mfa{}'.format(i))
            if 'auth-mfa-form' in self._content:
                self.log('MFA - one time password')
                form = soup.find('form', id='auth-mfa-form')
                ok = self._submitInput(self._text(form.p if form else None), 'otpCode', 'form#auth-mfa-form', remember='rememberDevice')
            elif 'name="claimspicker"' in self._content:
                ok = self._claimsPicker(soup)
            elif 'auth-select-device-form' in self._content:
                ok = self._selectDevice(soup)
            elif 'verification-code-form' in self._content:
                self.log('MFA - approval code')
                form = soup.find('form', id='verification-code-form')
                msg = os.linesep.join(self._text(t) for t in soup.find_all('span', class_='transaction-approval-word-break'))
                ok = self._submitInput(msg or self._text(form), 'otpCode', 'form#verification-code-form')
            elif 'cvf-widget-form' in self._content:
                ok = self._cvfForm(soup)
            elif 'pollingForm' in self._content:
                ok = self._pollApproval(soup)
            elif 'resend-approval-form' in self._content:
                ok = self._resendApproval(soup)
            else:
                self.log('Captcha requested, not supported')
                xbmcgui.Dialog().ok(self.getInfo('name'), self.getTranslation(30072))
                return False
            if not ok:
                return False
        return False

    def _submitInput( self, prompt, control, selector, remember=None ):
        """
        Ask the user for a verification code and post it with the given form
        """
        inp = self.getUserInput(prompt or self.getInfo('name'), '')
        if not inp or not self._selectForm(selector) or not self._setControl(control, inp):
            return False
        if remember and self._hasControl(remember):
            self._br.form.set_checkbox({remember: True})
        self._getLogonResponse()
        return True

    def _claimsPicker( self, soup ):
        """
        Amazon asks where to send the verification code or just to confirm sending it
        """
        self.log('MFA - claims picker')
        form = soup.find('form', attrs={'name': 'claimspicker'})
        heading = self._text(form.find('h1')) or self.getInfo('name')
        options = [(self._text(o), o.input['name'], o.input['value'])
                   for o in form.find_all('div', attrs={'data-a-input-name': 'option'}) if o.input]
        if not self._selectForm('form[name="claimspicker"]'):
            return False
        if options:
            sel = xbmcgui.Dialog().select(heading, [o[0] for o in options])
            if sel < 0 or not self._setControl(options[sel][1], options[sel][2]):
                return False
        else:
            rows = form.find_all('div', class_='a-row')
            text = self._text(rows[1]) if len(rows) > 1 else self._text(form)
            if not xbmcgui.Dialog().yesno(heading, text):
                return False
        self._getLogonResponse()
        return True

    def _selectDevice( self, soup ):
        self.log('MFA - select device')
        form = soup.find('form', id='auth-select-device-form')
        choices = [(self._text(l), l.input['name'], l.input['value']) for l in form.find_all('label') if l.input]
        heading = self._text(form.parent.find('p')) or self.getInfo('name')
        sel = xbmcgui.Dialog().select(heading, [c[0] for c in choices]) if choices else -1
        if sel < 0 or not self._selectForm('form#auth-select-device-form') or not self._setControl(choices[sel][1], choices[sel][2]):
            return False
        self._getLogonResponse()
        return True

    def _cvfForm( self, soup ):
        """
        CVF widget: a code sent by SMS / e-mail, a security question or a captcha
        """
        form = soup.find('form', class_='cvf-widget-form')
        inp = form and (form.find('input', attrs={'name': 'code'}) or form.find('input', attrs={'name': re.compile(r'^dcq_question')}))
        if not inp:
            if form and form.find('img', alt='captcha'):
                xbmcgui.Dialog().ok(self.getInfo('name'), self.getTranslation(30072))
            self.log('Unknown CVF form')
            return False
        self.log('MFA - {}'.format(inp['name']))
        label = form.find(class_='cvf-widget-input-code-label') or form.find('label')
        return self._submitInput(self._text(label), inp['name'], 'form.cvf-widget-form')

    def _resendApproval( self, soup ):
        """
        Amazon could not deliver the code and offers another channel, e.g. WhatsApp instead of SMS
        """
        self.log('MFA - resend approval')
        form = soup.find('form', id='resend-approval-form')
        container = form.find_parent(class_='chimera-body-container') or form.parent
        heading = self._text(form.find(class_='a-button-text')) or self.getInfo('name')
        if not xbmcgui.Dialog().yesno(heading, self._text(container)) or not self._selectForm('form#resend-approval-form'):
            return False
        self._getLogonResponse()
        return True

    def _pollApproval( self, soup ):
        """
        Amazon sent an approval request to another device, the sign-in page polls for the result
        """
        self.log('MFA - waiting for approval')
        message = os.linesep.join(self._text(t) for t in soup.find_all('span', class_='transaction-approval-word-break'))
        page_url = self._br.url
        query = urlparse.parse_qs(urlparse.urlparse(page_url).query)
        return_to = query.get('openid.return_to', [self.musicURL.format(self.credentials.USERTLD)])[0]
        dialog = xbmcgui.DialogProgress()
        dialog.create(self.getInfo('name'), message)
        try:
            while True:
                for _ in range(50):
                    if dialog.iscanceled():
                        return False
                    xbmc.sleep(100)
                self._open(page_url)
                if not self._selectForm('form#pollingForm'):
                    return False
                self._getLogonResponse()
                status = self._parseHTML(self._content).find('input', attrs={'name': 'transactionApprovalStatus'})
                status = status['value'] if status else ''
                self.log('Approval status: {}'.format(status))
                if status in ('TransactionCompleted', 'TransactionCompletionTimeout'):
                    self._open(return_to)
                    return True
                if status in ('TransactionExpired', 'TransactionResponded'):
                    return False
        finally:
            dialog.close()

    def _checkConfig( self ):
        """
        After login, load the web player configuration which carries the tokens for the API calls
        """
        app_config = self.fetchAppConfig()
        if not app_config or not app_config.get('tier'):
            self.log('No tier available, logon was not successful.')
            return False
        self._appConfig( app_config )
        self.saveCookie( self.credentials.COOKIE )
        return True

    def fetchAppConfig( self ):
        """
        The web player loads its configuration via POST /config.json instead of embedding it in the HTML
        """
        url = '{}/config.json?skipToken=false'.format( self.musicURL.format( self.credentials.USERTLD ) )
        head = {
            'Accept': 'application/json',
            'Accept-Language': self._acceptLanguage(),
            'User-Agent': self.userAgent
        }
        resp = requests.post( url=url, headers=head, cookies=self.credentials.COOKIE )
        if resp.status_code != 200:
            self.log('config.json failed: {} {}'.format(resp.status_code, resp.reason))
            return None
        app_config = resp.json()
        if self.G['logging']:
            self.log('config.json keys: {}, tier: {}'.format(sorted(app_config), app_config.get('tier')))
        return app_config

    def _appConfig( self, app_config ):
        """
        Obtain access token and other important information
        :param array app_config: The application configuration
        """
        #self.log(app_config)
        self.credentials.ACCESSTOKEN =       'Bearer {}'.format(app_config['accessToken'])
        self.credentials.CSRF_TOKEN =        app_config['csrf']['token']
        self.credentials.CSRF_TS =           app_config['csrf']['ts']
        self.credentials.CSRF_RND =          app_config['csrf']['rnd']
        self.credentials.DEVICEID =          app_config['deviceId']
        self.credentials.CUSTOMERID =        app_config['customerId']
        self.credentials.MARKETPLACEID =     app_config['marketplaceId']
        self.credentials.DEVICETYPE =        app_config['deviceType']
        self.credentials.MUSICTERRITORY =    app_config['musicTerritory']
        self.credentials.LOCALE =            app_config['displayLanguage']
        self.credentials.CUSTOMERLANG =      app_config['musicTerritory'].lower()
        self.credentials.REGION =            app_config['siteRegion']
        self.set_userTLD(
            self.checkUserTLD(
                app_config['musicTerritory'].lower(),
                self.G['TLDlist']
            )
        )

        if app_config['tier'] == 'UNLIMITED_HD':
            self.credentials.ACCESSTYPE = 'UNLIMITED'
        else:
            self.credentials.ACCESSTYPE =  app_config['tier']
