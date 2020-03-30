from threading import Thread
from time import sleep, strptime, mktime
import json
import logging
import socket

class GpsPoller:
    def __init__(self):
        self._log = logging.getLogger("EVNotiPi/GPSPoller")
        self._thread = None
        self._gpsd = ('localhost', 2947)
        self._last_fix = {
            'device': None,
            'mode': 0,
            'latitude': None,
            'longitude': None,
            'speed': None,
            'altitude': None,
            'time': None,
            'xdop': None,
            'ydop': None,
            'vdop': None,
            'tdop': None,
            'hdop': None,
            'gdop': None,
            'pdop': None,
                }
        self._running = False

    def run(self):
        self._running = True
        s = None
        while self._running:
            try:
                if s:
                    try:
                        data = s.recv(4096)
                        for line in data.split(b'\r\n'):
                            if len(line) == 0:
                                continue
                            try:
                                fix = json.loads(line)
                                if 'class' not in fix:
                                    continue

                                if fix['class'] == 'TPV':
                                    fix_time = mktime(strptime(fix['time'][:23],
                                                               "%Y-%m-%dT%H:%M:%S.%f"))

                                    self._last_fix.update({
                                        'device':    fix['device'],
                                        'mode':      fix['mode'],
                                        'latitude':  fix.get('lat'),
                                        'longitude': fix.get('lon'),
                                        'speed':     fix.get('speed'),
                                        'altitude':  fix.get('alt'),
                                        'time':      fix_time,
                                        })
                                elif fix['class'] == 'SKY':
                                    self._last_fix.update({
                                        'xdop': fix.get('xdop'),
                                        'ydop': fix.get('ydop'),
                                        'vdop': fix.get('vdop'),
                                        'tdop': fix.get('tdop'),
                                        'hdop': fix.get('hdop'),
                                        'gdop': fix.get('gdop'),
                                        'pdop': fix.get('pdop'),
                                        })

                            except json.decoder.JSONDecodeError:
                                self._log.error("JSONDecodeError %s", line)
                    except socket.timeout:
                        pass
                else:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        s.connect(self._gpsd)
                        s.settimeout(1)
                        s.recv(1024)
                        s.sendall(b'?WATCH={"enable":true,"json":true};')
                    except OSError as e:
                        s.close()
                        s = None
            except (StopIteration, ConnectionResetError, OSError):
                s.close()
                s = None
                self._last_fix = None
                sleep(1)

    def fix(self):
        return self._last_fix

    def start(self):
        self._running = True
        self._thread = Thread(target=self.run, name="EVNotiPi/GPS")
        self._thread.start()

    def stop(self):
        self._running = False
        self._thread.join()

    def checkWatchdog(self):
        return self._thread.is_alive()

if __name__ == '__main__':
    gps = GpsPoller()
    gps.run()

