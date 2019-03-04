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
from wifi_ctrl import WiFiCtrl
import RPi.GPIO as GPIO
from subprocess import check_call

sys.path.append('EVNotifyAPI/libs/python')
sys.path.append('dongles')
sys.path.append('cars')

import evnotifyapi

PIN_IGN   = 21
LOOP_DELAY = 2
NO_DATA_DELAY = 600 # 10 min
CHARGE_COOLDOWN_DELAY = 3600 * 6 # 6 h

class POLL_DELAY(Exception): pass

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
        sleep(3)

if cartype == 'IONIQ_BEV':
    from IONIQ_BEV import IONIQ_BEV as CAR
    #from IONIQ_FAKE import IONIQ_FAKE as CAR
elif cartype == 'KONA_EV':
    from KONA_EV import KONA_BEV as CAR

dongle = DONGLE(config['dongle'])
car = CAR(dongle)

gps = GpsPoller()
gps.start()

wifi = WiFiCtrl()

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_IGN, GPIO.IN)

main_running = True
last_charging = time()
delay_poll_until = time()

try:
    while main_running:
        now = time()
        try:
            if delay_poll_until > now and GPIO.input(PIN_IGN) == 1:
                raise POLL_DELAY()      # Skip delay if car on

            data = car.getData()
            fix = gps.fix()
        except DONGLE.CAN_ERROR as e:
            print(e)
        except DONGLE.NO_DATA:
            print("NO DATA - delay polling")
            delay_poll_until = now + NO_DATA_DELAY
        except POLL_DELAY:
            pass

        else:
            print(data)
            try:
                EVNotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
                EVNotify.setExtended(data['EXTENDED'])
                if fix and fix.mode > 1: # mode: GPS-fix quality
                    g ={
                        'latitude':  fix.latitude,
                        'longitude': fix.longitude,
                        'speed': fix.speed,
                        }
                    print(g)
                    EVNotify.setLocation({'location': g})

            except evnotifyapi.CommunicationError as e:
                print(e)

            if data['EXTENDED']['charging'] == 1 or GPIO.input(PIN_IGN) == 0:
                last_charging = now
                wifi.enable()
            else:
                wifi.disable()

        finally:
            if GPIO.input(PIN_IGN) == 1:
                print("ignition off detected")
            if now - last_charging > CHARGE_COOLDOWN_DELAY and GPIO.input(PIN_IGN) == 1:
                print("Not charging and ignition off => Shutdown")
                check_call(['/usr/bin/systemctl','poweroff'])

            sys.stdout.flush()

            if main_running: sleep(LOOP_DELAY)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
finally:
    print("Exiting ...")
    GPIO.cleanup()
    gps.stop()
    print("Bye.")

