import gps
import threading

class GpsPoller(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.gps = gps
        self.gpsd = None
        self.fix = None

    def run(self):
        self.running = True
        while self.running:
            try:
                if self.gpsd:
                    self.gpsd.next()
                    self.fix = self.gpsd.fix
                else:
                    self.gpsd = self.gps.gps(mode=self.gps.WATCH_ENABLE)
            except (StopIteration, ConnectionResetError, OSError):
                self.gpsd = None
                self.fix = None
                sleep(1)

    def stop(self):
        self.running = False
        self.join()

