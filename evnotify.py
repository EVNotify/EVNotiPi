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

PIN_IGN   = 21
PIN_12VOK = 20
LOOP_DELAY = 2
DATA_BUFFER_MAX_LEN = 256

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
cartype = None
while cartype == None:
    try:
        cartype = EVNotify.getSettings()['car']
    except EVNotify.CommunicationError as e:
        print("Waiting for network connectivity")
        sleep(3s)

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
GPIO.setup(PIN_IGN, GPIO.IN)
GPIO.setup(PIN_12VOK, GPIO.IN)

VCCstatCntr = 0
main_running = True
last_charging = time()
data_buffer = []

try:
    while main_running:
        now = time()
        try:
            data_buffer.append([car.getData(), gps.fix])
            if len(data_buffer) > DATA_BUFFER_MAX_LEN: del data_buffer[0]
        except DONGLE.CAN_ERROR as e:
            print(e)

        else:
            print(data_buffer[-1])
            try:
                while len(data_buffer) > 0:
                    data,fix = data_buffer[0]

                    EVNotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
                    EVNotify.setExtended(data['EXTENDED'])
                    if fix and fix.mode > 1: # mode: GPS-fix quality
                        g ={
                            'latitude':  fix.latitude,
                            'longitude': fix.longitude,
                            'gps_speed': fix.speed,
                            #'accuracy':  gps.fix.epx,
                            #'timestamp': strptime(gps.fix.time,'%Y-%m-%dT%H:%M:%S.000Z'),
                            }
                        print(g)
                        EVNotify.setLocation({'location': g})

                    del data_buffer[0]

            except evnotifyapi.CommunicationError as e:
                print(e)

            if data['EXTENDED']['charging'] == 1 or GPIO.input(PIN_IGN) == 0:
                last_charging = now

        finally:
            if GPIO.input(PIN_12VOK) == 1:
                VCCstatCntr += 1
            elif VCCstatCntr > 0:
                VCCstatCntr -=1

            if VCCstatCntr > 120 / LOOP_DELAY:    # If VCC is below warning for 2 minutes
                print("12V check failed, shutting down")
                main_running = False
                check_call(['/usr/bin/systemctl','poweroff'])

            if GPIO.input(PIN_IGN) == 1:
                print("ignition off detected")
            if now - last_charging > 300 and GPIO.input(PIN_IGN) == 1: # 5min
                print("Not charging and ignition off => Shutdown")
                main_running = False
                check_call(['/usr/bin/systemctl','poweroff'])

            if main_running: sleep(LOOP_DELAY)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
finally:
    gps.stop()
    print("Bye.")

