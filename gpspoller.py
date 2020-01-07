import sys
import socket
from threading import Thread
from time import time,sleep
from math import isnan
import json
import logging

class GpsPoller:
    def __init__(self):
        self.log = logging.getLogger("EVNotiPi/GPSPoller")
        self.thread = None
        self.gpsd = ('localhost', 2947)
        self.last_fix = {
                'device': None,
                'mode': 0,
                'latitude': None,
                'longitude': None,
                'speed': None,
                'altitude': None,
                'xdop': None,
                'ydop': None,
                'vdop': None,
                'tdop': None,
                'hdop': None,
                'gdop': None,
                'pdop': None,
                }
        self.distance = 0

    def run(self):
        self.running = True
        s = None
        while self.running:
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
                                    self.last_fix.update({
                                        'device':    fix['device'],
                                        'mode':      fix['mode'],
                                        'latitude':  fix['lat'],
                                        'longitude': fix['lon'],
                                        'speed':     fix['speed'],
                                        'altitude':  fix['alt'] if fix['mode'] > 2 else None,
                                        })
                                elif fix['class'] == 'SKY':
                                    self.last_fix.update({
                                        'xdop': fix['xdop'],
                                        'ydop': fix['ydop'], 
                                        'vdop': fix['vdop'], 
                                        'tdop': fix['tdop'], 
                                        'hdop': fix['hdop'], 
                                        'gdop': fix['gdop'], 
                                        'pdop': fix['pdop'], 
                                        })
                            except json.decoder.JSONDecodeError:
                                self.log.error("JSONDecodeError %s", line)
                    except socket.timeout:
                        pass
                else:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    try:
                        s.connect(self.gpsd)
                        s.settimeout(1)
                        s.recv(1024)
                        s.sendall(b'?WATCH={"enable":true,"json":true};')
                    except OSError as e:
                        s.close()
                        s = None
            except (StopIteration, ConnectionResetError, OSError):
                self.last_fix = None
                sleep(1)

    def fix(self):
        return self.last_fix

    def start(self):
        self.running = True
        self.thread = Thread(target = self.run, name = "EVNotiPi/GPS")
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def checkWatchdog(self):
        return self.thread.is_alive()

if __name__ == '__main__':
    gps = GpsPoller()
    gps.run()

