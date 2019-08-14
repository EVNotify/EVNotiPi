#!/usr/bin/env python3

from gpspoller import GpsPoller
from time import sleep,time
import evnotifyapi
import json
import os
import re
import sys
import signal

LOOP_DELAY = 5
EVN_SETTINGS_DELAY = 300
ABORT_NOTIFICATION_DELAY = 60
POLL_THRESHOLD_VOLT = 13

class SKIP_POLL(Exception): pass

# load config
with open('config.json', encoding='utf-8') as config_file:
    config = json.loads(config_file.read())

# load api lib
EVNotify = evnotifyapi.EVNotify(config['akey'], config['token'])

settings = None

if 'cartype' in config:
    cartype = config['cartype']
else:
    print("Get settings from backend")
    while settings == None:
        try:
            settings = EVNotify.getSettings()
        except evnotifyapi.CommunicationError as e:
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

# Init GPS interface
gps = GpsPoller()
gps.start()

# Init some variables
main_running = True
now = time()
last_charging = now
last_charging_soc = 0
last_data = now
last_evn_settings_poll = now

# Init SOC notifications
chargingStartSOC = 0
currentSOC = 0
socThreshold = int(config['socThreshold']) if 'socThreshold' in config else 0
notificationSent = False
abortNotificationSent = False
print("Notification threshold: {}".format(socThreshold))

# Set up signal handling
def exit_gracefully(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)

car_off_skip_poll = False

print("Starting main loop")
try:
    while main_running:
        now = time()
        try:
            if car_off_skip_poll:       # Skip polling until car on voltage is detected again
                if dongle.getObdVoltage() < POLL_THRESHOLD_VOLT:
                    raise SKIP_POLL
                else:
                    print("Car on detected. Resume polling.")
                    car_off_skip_poll = False

            data = car.getData()
            fix = gps.fix()
            last_data = now
            is_charging = False

            if fix and fix.mode > 1:
                location = {
                        'latitude':  fix.latitude,
                        'longitude': fix.longitude,
                        'speed': fix.speed
                        }
                if fix.mode > 2:
                    location['altitude'] = fix.altitude
            else:
                location = None

            #print(data)
            last_evn_transmit = now
            if 'SOC_DISPLAY' in data and 'SOC_BMS' in data:
                EVNotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
                currentSOC = data['SOC_DISPLAY'] or data['SOC_BMS']

            if 'EXTENDED' in data:
                EVNotify.setExtended(data['EXTENDED'])
                is_charging = True if 'charging' in data['EXTENDED'] and \
                        data['EXTENDED']['charging'] == 1 else False
                is_connected = True if ('normalChargePort' in data['EXTENDED'] \
                        and data['EXTENDED']['normalChargePort'] == 1) \
                        or ('rapidChargePort' in data['EXTENDED'] \
                        and data['EXTENDED']['rapidChargePort'] == 1) else False

                if is_charging:
                    last_charging = now
                    last_charging_soc = currentSOC

                if is_charging and 'socThreshold' not in config and \
                        now - last_evn_settings_poll > EVN_SETTINGS_DELAY:
                    try:
                        s = EVNotify.getSettings()
                        # following only happens if getSettings is
                        # successful, else jumps into exception handler
                        settings = s
                        last_evn_settings_poll = now

                        if s['soc'] and s['soc'] != socThreshold:
                            socThreshold = int(s['soc'])
                            print("New notification threshold: {}".format(socThreshold))

                    except evnotifyapi.CommunicationError:
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
                elif not is_connected:   # Rearm notification
                    chargingStartSOC = 0
                    notificationSent = False
                    abortNotificationSent = False

            if location and not is_charging and not is_connected:
                EVNotify.setLocation({'location': location})

        except evnotifyapi.CommunicationError as e:
            print(e)
        except DONGLE.CAN_ERROR as e:
            print(e)
        except DONGLE.NO_DATA as e:
            print(e)
            volt = dongle.getObdVoltage()
            if volt and volt < POLL_THRESHOLD_VOLT:
                print("Car off detected. Stop polling until car on.")
                car_off_skip_poll = True
        except SKIP_POLL as e:
            pass
        except CAR.NULL_BLOCK as e:
            print(e)

        finally:
            try:
                # Try to detect aborted charging
                if not abortNotificationSent \
                        and now - last_charging > ABORT_NOTIFICATION_DELAY \
                        and chargingStartSOC > 0 and last_charging_soc < socThreshold:
                    print("No response detected, send abort notification")
                    EVNotify.sendNotification(True)
                    abortNotificationSent = True

            except evnotifyapi.CommunicationError as e:
                print("Sending of notificatin failed! {}".format(e))

            # Flush the output buffer
            sys.stdout.flush()

            if main_running:
                # Compensate for the running time of the loop
                loop_delay = LOOP_DELAY - (time() - now)
                if loop_delay > 0:
                    sleep(loop_delay)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False

finally:
    print("Exiting ...")
    gps.stop()
    print("Bye.")

