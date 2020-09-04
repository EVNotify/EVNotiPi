""" Interface to gpsd """
from threading import Thread
from time import sleep, strptime, mktime
import json
import logging
import socket


def empty_fix():
    """ Return an empty fix so all fields are guaranteed to exist. """
    return {
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


class GpsPoller:
    """ Thread that continously reads data from gpsd. """

    def __init__(self):
        self._log = logging.getLogger("EVNotiPi/GPSPoller")
        self._thread = None
        self._gpsd = ('localhost', 2947)
        self._last_fix = empty_fix()
        self._running = False

    def run(self):
        """ The reader thread. """
        self._running = True
        gps_sock = None
        while self._running:
            try:
                if gps_sock:
                    data = gps_sock.recv(4096)
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
                                    'xdop': fix.get('xdop', None),
                                    'ydop': fix.get('ydop', None),
                                    'vdop': fix.get('vdop', None),
                                    'tdop': fix.get('tdop', None),
                                    'hdop': fix.get('hdop', None),
                                    'gdop': fix.get('gdop', None),
                                    'pdop': fix.get('pdop', None),
                                })

                        except json.decoder.JSONDecodeError:
                            self._log.error("JSONDecodeError %s", line)
                else:
                    gps_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    gps_sock.connect(self._gpsd)
                    gps_sock.settimeout(1)
                    gps_sock.recv(1024)
                    gps_sock.sendall(b'?WATCH={"enable":true,"json":true};')
            except socket.timeout:
                sleep(0.1)
            except (StopIteration, ConnectionResetError, OSError) as err:
                self._log.info('Problem encountered. Resetting socket. (%s)', err)
                gps_sock.close()
                gps_sock = None
                self._last_fix = empty_fix()
                sleep(1)

    def fix(self):
        """ Return the last fix. """
        return self._last_fix

    def start(self):
        """ Start the poller thread. """
        self._running = True
        self._thread = Thread(target=self.run, name="EVNotiPi/GPS")
        self._thread.start()

    def stop(self):
        """ Stop the poller thread. """
        self._running = False
        self._thread.join()

    def check_thread(self):
        """ Return running state if the poller thread. """
        return self._thread.is_alive()


if __name__ == '__main__':
    gps = GpsPoller()
    gps.run()
