import requests
import logging

class CanError(Exception): pass
class NoData(Exception): pass

class CanDebug:
    def __init__(self, config, cartype, akey):
        self.log = logging.getLogger("EVNotiPi/CanDebug")
        self.session = requests.Session()
        self.url = config['debug']['url']
        self.user = config['debug'].get('user')
        self.pwd  = config['debug'].get('pass')
        self.cartype = cartype
        self.akey = akey
        self.data_queue = []

    def debug(self, cantx, canrx, cmd, data):
        json = {
            'cantx': cantx,
            'canrx': canrx,
            'command': cmd,
            'rawdata': data
            }
        self.data_queue.append(json)
        try:
            self.session.post(self.url, data=self.data_queue,
                              auth=(self.user, self.pwd), timeout=0.1)
            self.data_queue.clear()
        except requests.exceptions.Timeout as e:
            self.log.info("Timeout occured %s", e)

class OBDDongle:
    def __init__(self, config):
        if 'debug' in config and config['debug']:
            self.candebug = CanDebug(config)
        else:
            self.candebug = None

    def pushDebug(self, cantx, canrx, cmd, data):
        if self.candebug:
            self.candebug.debug(cantx, canrx, cmd, data)

