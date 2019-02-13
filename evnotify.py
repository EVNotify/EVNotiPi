#!/usr/bin/env python3

import re
import time
import string
import io
import json
#import importlib
import sys
from time import sleep
import threading
import gps

sys.path.append('EVNotifyAPI/libs/python')
sys.path.append('dongles')
sys.path.append('cars')

import evnotifyapi

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

# load config
with open('config.json', encoding='utf-8') as config_file:
    config = json.loads(config_file.read())

# load api lib
EVNotify = evnotifyapi.EVNotify(config['akey'], config['token'])

# Init ODB2 adapter
if config['dongle']['type'] == 'ELM327':
    from ELM327 import ELM327 as DONGLE
elif config['dongle']['type'] == 'PiOBD2Hat':
    from PiOBD2Hat import PiOBD2Hat as DONGLE
else:
    raise Exception('Unknown dongle %s' % config['dongle']['type'])

dongle = DONGLE(config['dongle'])

# Init car interface
cartype = EVNotify.getSettings()['car']
if cartype == 'IONIQ_BEV':
    from IONIQ_BEV import IONIQ_BEV as CAR
    #from IONIQ_FAKE import IONIQ_FAKE as CAR
elif cartype == 'KONA_EV':
    from KONA_EV import KONA_BEV as CAR

car = CAR(dongle)

gps = GpsPoller()
gps.start()
main_running = True
try:
    while main_running:
        try:
            data = car.getData()
        except DONGLE.CAN_ERROR as e:
            print(e)

        else:
            print(data)
            EVNotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
            EVNotify.setExtended(data['EXTENDED'])
            if gps.fix and gps.fix.mode > 1: # mode: GPS-fix quality
                g ={
                    'latitude':  gps.fix.latitude,
                    'longitude': gps.fix.longitude,
                    'gps_speed': gps.fix.speed,
                    #'accuracy':  gps.fix.epx,
                    #'timestamp': strptime(gps.fix.time,'%Y-%m-%dT%H:%M:%S.000Z'),
                    }
                print(g)
                EVNotify.setLocation({'location': g})
        finally:
            if main_running: sleep(2)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
finally:
    gps.stop()
    print("Bye.")

