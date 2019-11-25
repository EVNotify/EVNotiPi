from time import time, sleep
from threading import Thread
from readerwriterlock import rwlock
from dongle import NoData, CanError
import logging

def ifbu(in_bytes): return int.from_bytes(in_bytes, byteorder='big', signed=False)
def ifbs(in_bytes): return int.from_bytes(in_bytes, byteorder='big', signed=True)
def ffbu(in_bytes): return float(int.from_bytes(in_bytes, byteorder='big', signed=False))
def ffbs(in_bytes): return float(int.from_bytes(in_bytes, byteorder='big', signed=True))

class DataError(Exception): pass

class Car:
    def __init__(self, config, dongle):
        self.log = logging.getLogger("EVNotiPi/Car")
        self.config = config
        self.dongle = dongle
        self.poll_interval = config['interval']
        self.thread = None
        self.data = {}
        self.datalock = rwlock.RWLockWrite()
        self.skip_polling = False
        self.running = False
        self.last_data = 0
        self.watchdog = time()
        self.watchdog_timeout = self.poll_interval * 10 if self.poll_interval else 10
        self.data_callbacks = []

    def start(self):
        self.running = True
        self.thread = Thread(target = self.pollData)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def pollData(self):
        while self.running:
            now = time()
            self.watchdog = now

            with self.datalock.gen_wlock():
                if not self.skip_polling or self.dongle.isCarAvailable():
                    if self.skip_polling:
                        self.log.info("Resume polling.")
                        self.skip_polling = False
                    try:
                        self.data = self.readDongle()
                        self.last_data = now
                    except CanError as e:
                        self.log.warning(e)
                    except NoData:
                        self.log.info("NO DATA")
                        if not self.dongle.isCarAvailable():
                            self.log.info("Car off detected. Stop polling until car on.")
                            self.skip_polling = True
                else:
                    self.data = {}

                if self.dongle.watchdog:
                    thresholds = self.dongle.watchdog.getThresholds()
                    if not 'ADDITIONAL' in self.data:
                        self.data['ADDITIONAL'] = {}
                    if not 'timestamp' in self.data:
                        self.data['timestamp'] = now

                    volt = self.dongle.getObdVoltage()
                    #if 'EXTENDED' in self.data and 'auxBatteryVoltage' in self.data['EXTENDED']:
                    #    if abs(self.data['EXTENDED']['auxBatteryVoltage'] - volt) > 0.1:
                    #        self.dongle.calibrateObdVoltage(self.data['EXTENDED']['auxBatteryVoltage'])
                    #        volt = self.dongle.getObdVoltage()

                    self.data['ADDITIONAL'].update ({
                        'obdVoltage':               volt,
                        'startupThreshold':         thresholds['startup'],
                        'shutdownThreshold':        thresholds['shutdown'],
                        'emergencyThreshold':       thresholds['emergency'],
                        })

                for cb in self.data_callbacks:
                    cb(self.data)

            if self.running and self.poll_interval:
                runtime = time() - now
                interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                sleep(interval)

    def getData(self):
        with self.datalock.gen_rlock():
            return self.data if len(self.data) > 0 else None

    def registerData(self, callback):
        self.data_callbacks.append(callback)

    def unregisterData(self, callback):
        self.data_callbacks.remove(callback)

    def checkWatchdog(self):
        return (time() - self.watchdog) <= self.watchdog_timeout
