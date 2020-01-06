import sys
import gps
from threading import Thread
from time import time,sleep
from math import isnan

class GpsPoller:
    def __init__(self):
        self.thread = None
        self.gps = gps
        self.gpsd = None
        self.last_fix = None
        self.distance = 0

    def run(self):
        self.running = True
        while self.running:
            try:
                if self.gpsd:
                    if self.gpsd.waiting(timeout=1):
                        self.gpsd.next()

                        fix = self.gpsd.fix
                        fix.device = self.gpsd.device
                        fix.gdop = self.gpsd.gdop if not isnan(self.gpsd.gdop) else None
                        fix.pdop = self.gpsd.pdop if not isnan(self.gpsd.pdop) else None
                        fix.hdop = self.gpsd.hdop if not isnan(self.gpsd.hdop) else None
                        fix.vdop = self.gpsd.vdop if not isnan(self.gpsd.vdop) else None

                        self.last_fix = fix
                else:
                    self.gpsd = self.gps.gps(mode=self.gps.WATCH_ENABLE)
            except (StopIteration, ConnectionResetError, OSError):
                self.gpsd = None
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

