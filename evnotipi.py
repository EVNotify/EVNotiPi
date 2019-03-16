#!/usr/bin/env python3

from gpspoller import GpsPoller
from subprocess import check_call
from time import sleep,time
import RPi.GPIO as GPIO
import evnotifyapi
import io
import json
import os
import re
import string
import sys

PIN_IGN    = 21
LOOP_DELAY = 5
NO_DATA_DELAY = 600 # 10 min
CHARGE_COOLDOWN_DELAY = 3600 * 6 # 6 h  set to None to disable auto shutdown

class POLL_DELAY(Exception): pass

# load config
with open('config.json', encoding='utf-8') as config_file:
    config = json.loads(config_file.read())

# load api lib
EVNotify = evnotifyapi.EVNotify(config['akey'], config['token'])

settings = None

if 'cartype' in config:
    cartype = config['cartype']
else:
    # get settings from backend
    while settings == None:
        try:
            settings = EVNotify.getSettings()
        except EVNotify.CommunicationError as e:
            print("Waiting for network connectivity")
            sleep(3)

    cartype = settings['car']

# Load OBD2 interface module
if not "{}.py".format(config['dongle']['type']) in os.listdir('dongles'):
    raise Exception('Unknown dongle {}'.format(config['dongle']['type']))

# Init ODB2 adapter
sys.path.insert(0, 'dongles')
exec("from {0} import {0} as DONGLE".format(config['dongle']['type']))
sys.path.remove('dongles')

# Only accept a few characters, do not trust stuff from the Internet
if re.match('^[a-zA-Z0-9_-]+$',cartype) == None:
    raise Exception('Invalid characters in cartype')

if not "{}.py".format(cartype) in os.listdir('cars'):
    raise Exception('Unknown car {}'.format(cartype))

sys.path.insert(0, 'cars')
exec("from {0} import {0} as CAR".format(cartype))
sys.path.remove('cars')

dongle = DONGLE(config['dongle'])
car = CAR(dongle)

# Set up GPIOs
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN_IGN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Init GPS interface
gps = GpsPoller()
gps.start()

# Init some variables
main_running = True
last_charging = time()
delay_poll_until = time()

# Init SOC notifications
chargingStartSOC = 0
socThreshold = int(config['socThreshold']) if 'socThreshold' in config else 0
notificationSent = False
print("Notification threshold: {}".format(socThreshold))

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
        except:
            raise

        else:
            print(data)
            try:
                EVNotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
                currentSOC = data['SOC_DISPLAY'] or data['SOC_BMS']

                if 'EXTENDED' in data:
                    EVNotify.setExtended(data['EXTENDED'])
                    is_charging = True if 'charging' in data['EXTENDED'] and \
                            data['EXTENDED']['charging'] == 1 else False

                    if is_charging and 'socThreshold' not in config:
                        try:
                            s = EVNotify.getSettings()
                            # following only happens if getSettings is
                            # successful, else jumps into exception handler
                            settings = s

                            if s['soc'] != socThreshold:
                                socThreshold = int(s['soc'])
                                print("New notification threshold: {}".format(socThreshold))

                        except EVNotify.CommunicationError:
                            pass

                    # track charging started
                    if is_charging and chargingStartSOC == 0:
                        chargingStartSOC = currentSOC or 0
                    # check if notification threshold reached
                    elif is_charging and chargingStartSOC < socThreshold and \
                            currentSOC >= socThreshold and not notificationSent:
                        print("Notification threshold reached")
                        EVNotify.sendNotification()
                        notificationSent = True
                    elif not is_charging:   # Rearm notification
                        notificationSent = False

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
            except:
                raise

        finally:
            if GPIO.input(PIN_IGN) == 1:
                print("ignition off detected")

            if CHARGE_COOLDOWN_DELAY != None:
                if now - last_charging > CHARGE_COOLDOWN_DELAY and GPIO.input(PIN_IGN) == 1:
                    print("Not charging and ignition off => Shutdown")
                    check_call(['/bin/systemctl','poweroff'])

            sys.stdout.flush()

            if main_running: sleep(LOOP_DELAY)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
except:
    raise
finally:
    print("Exiting ...")
    GPIO.cleanup()
    gps.stop()
    print("Bye.")

