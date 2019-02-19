#!/usr/bin/env python3

import re
import time
import string
import io
import json
#import importlib
import sys
from time import sleep,time
from gpspoller import GpsPoller
import RPi.GPIO as GPIO
from subprocess import check_call

sys.path.append('EVNotifyAPI/libs/python')
sys.path.append('dongles')
sys.path.append('cars')

import evnotifyapi

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

# Init car interface
try:
    cartype = EVNotify.getSettings()['car']
except EVNotify.CommunicationError as e:
    print('Communication to server failed!')
    print(e)
    exit(1)

if cartype == 'IONIQ_BEV':
    from IONIQ_BEV import IONIQ_BEV as CAR
    #from IONIQ_FAKE import IONIQ_FAKE as CAR
elif cartype == 'KONA_EV':
    from KONA_EV import KONA_BEV as CAR

dongle = DONGLE(config['dongle'])
car = CAR(dongle)

gps = GpsPoller()
gps.start()
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.IN)
main_running = True
last_charging = time()

try:
    while main_running:
        now = time()
        try:
            data = car.getData()
        except DONGLE.CAN_ERROR as e:
            print(e)

        else:
            print(data)
            try:
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
            except evnotifyapi.CommunicationError as e:
                print(e)

            if data['EXTENDED']['charging'] == 1 or GPIO.input(21) == 0:
                last_charging = now

        finally:
            if now - last_charging > 300 and GPIO.input(21) == 1: # 5min
                print("Not charging and ignition off => Shutdown")
                main_running = False
                check_call(['/usr/bin/systemctl','poweroff'])

            if main_running: sleep(2)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
finally:
    gps.stop()
    print("Bye.")

