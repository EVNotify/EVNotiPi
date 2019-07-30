import sys
sys.path.append('/usr/local/lib/python3.7/site-packages')
import gps
import threading
from time import time,sleep

class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.gps = gps
        self.gpsd = None
        self.last_fix = None

    def run(self):
        self.running = True
        while self.running:
            try:
                if self.gpsd:
                    if self.gpsd.waiting(timeout=1):
                        self.gpsd.next()
                        self.last_fix = self.gpsd.fix
                else:
                    self.gpsd = self.gps.gps(mode=self.gps.WATCH_ENABLE)
            except (StopIteration, ConnectionResetError, OSError):
                self.gpsd = None
                self.last_fix = None
                sleep(1)

    def fix(self):
        return self.last_fix

    def stop(self):
        self.running = False
        self.join()

