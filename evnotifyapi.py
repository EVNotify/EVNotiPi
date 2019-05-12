import json
import requests

class EVNotify:

    class CommunicationError(Exception): pass

    def __init__(self, akey = None, token = None):
        self.RESTURL = 'https://app.evnotify.de/'
        self.session = requests.Session()
        self.akey = akey
        self.token = token

    def sendRequest(self, method, fnc, useAuthentication = False, params = {}):
        if useAuthentication:
            params['akey'] = self.akey
            params['token'] = self.token
        try:
            if method == 'get':
                return getattr(self.session, method)(self.RESTURL + fnc, params=params).json()
            else:
                return getattr(self.session, method)(self.RESTURL + fnc, json=params).json()

        except requests.exceptions.ConnectionError:
            raise EVNotify.CommunicationError()

    def getKey(self):
        return self.sendRequest('get', 'key')['akey']

    def register(self, akey, password):
        self.token = self.sendRequest('post', 'register', False, {
            "akey": akey,
            "password": password
        })['token']
        self.akey = akey
        return self.token

    def login(self, akey, password):
        self.token = self.sendRequest('post', 'login', False, {
            "akey": akey,
            "password": password
        })['token']
        self.akey = akey
        return self.token

    def changePassword(self, oldpassword, newpassword):
        return self.sendRequest('post', 'changepw', True, {
            "oldpassword": oldpassword,
            "newpassword": newpassword
        })['changed']

    def getSettings(self):
        return self.sendRequest('get', 'settings', True)['settings']

    def setSettings(self, settings):
        return self.sendRequest('put', 'settings', True, {
            "settings": settings
        })['settings']

    def setSOC(self, display, bms):
        return self.sendRequest('post', 'soc', True, {
            "display": display,
            "bms": bms
        })['synced']

    def getSOC(self):
        return self.sendRequest('get', 'soc', True)

    def setExtended(self, obj):
        return self.sendRequest('post', 'extended', True, obj)['synced']

    def getExtended(self):
        return self.sendRequest('get', 'extended', True)

    def getLocation(self):
        return self.sendRequest('get', 'location', True)

    def setLocation(self, obj):
        return self.sendRequest('post', 'location', True, obj)['synced']

    def renewToken(self, password):
        self.token = self.sendRequest('put', 'renewtoken', True, {
            "password": password
        })['token']
        return self.token

    def sendNotification(self, abort = False):
        return self.sendRequest('post', 'notification', True, {
            "abort": abort
        })['notified']
