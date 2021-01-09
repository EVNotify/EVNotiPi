""" Python interface for EVNotify API """

import requests

class CommunicationError(Exception): pass

class EVNotify:

    def __init__(self, akey=None, token=None):
        self._rest_url = 'https://app.evnotify.de/'
        self._session = requests.Session()
        self._session.headers.update({'User-Agent': 'PyEVNotifyApi/2'})
        self._akey = akey
        self._token = token
        self._timeout = 5

    def sendRequest(self, method, fnc, useAuthentication=False, data={}):
        params = {**data}

        if useAuthentication:
            params['akey'] = self._akey
            params['token'] = self._token

        try:
            if method == 'get':
                result = getattr(self._session, method)(self._rest_url + fnc,
                                                        params=params,
                                                        timeout=self._timeout)
            else:
                result = getattr(self._session, method)(self._rest_url + fnc,
                                                        json=params,
                                                        timeout=self._timeout)
            if result.status_code >= 400:
                raise CommunicationError("code({}) text({})"
                                         .format(result.status_code, result.text))

            return result.json()

        except requests.exceptions.ConnectionError:
            raise CommunicationError("connection failed")
        except requests.exceptions.Timeout:
            raise CommunicationError("timeout")


    def getKey(self):
        ret = self.sendRequest('get', 'key')

        if 'akey' not in ret:
            raise CommunicationError("return akey missing")

        return ret['akey']

    def getToken(self):
        return self._token

    def register(self, akey, password):
        ret = self.sendRequest('post', 'register', False, {
            "akey": akey,
            "password": password
        })

        if 'token' not in ret:
            raise CommunicationError("return token missing")

        self._token = ret['token']
        self._akey = akey

    def login(self, akey, password):
        ret = self.sendRequest('post', 'login', False, {
            "akey": akey,
            "password": password
        })

        if 'token' not in ret:
            raise CommunicationError("return token missing")

        self._token = ['token']
        self._akey = akey

    def changePassword(self, oldpassword, newpassword):
        ret = self.sendRequest('post', 'changepw', True, {
            "oldpassword": oldpassword,
            "newpassword": newpassword
        })

        return ret['changed'] if 'changed' in ret else None

    def getSettings(self):
        ret = self.sendRequest('get', 'settings', True)

        if 'settings' not in ret:
            raise CommunicationError("return settings missing")

        return ret['settings']

    def setSettings(self, settings):
        ret = self.sendRequest('put', 'settings', True, {
            "settings": settings
        })

        if 'settings' not in ret:
            raise CommunicationError()

    def setSOC(self, display, bms):
        ret = self.sendRequest('post', 'soc', True, {
            "display": display,
            "bms": bms
        })

        if 'synced' not in ret:
            raise CommunicationError("return settings missing")

    def getSOC(self):
        return self.sendRequest('get', 'soc', True)

    def setExtended(self, obj):
        ret = self.sendRequest('post', 'extended', True, obj)

        if 'synced' not in ret:
            raise CommunicationError("return synced missing")

    def getExtended(self):
        return self.sendRequest('get', 'extended', True)

    def getLocation(self):
        return self.sendRequest('get', 'location', True)

    def setLocation(self, obj):
        ret = self.sendRequest('post', 'location', True, obj)

        if 'synced' not in ret:
            raise CommunicationError("return synced missing")

    def renewToken(self, password):
        ret = self.sendRequest('put', 'renewtoken', True, {
            "password": password
        })

        if 'token' not in ret:
            raise CommunicationError("return token missing")

        self._token = ret['token']

        return self._token

    def sendNotification(self, abort=False):
        ret = self.sendRequest('post', 'notification', True, {
            "abort": abort
        })

        if 'notified' not in ret:
            raise CommunicationError("return notified missing")

        return ret['notified']
