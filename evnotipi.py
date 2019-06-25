#!/usr/bin/env python3

from gpspoller import GpsPoller
from subprocess import check_call, check_output
from time import sleep,time
from wifi_ctrl import WiFiCtrl
import RPi.GPIO as GPIO
import evnotifyapi
import io
import json
import os
import re
import string
import sys
import signal

PIN_CARON = 21
EVN_DELAY = 5
EVN_SETTINGS_DELAY = 300
NO_DATA_SLEEP = 600 # 10 min
DATA_WAIT = 300
ABORT_NOTIFICATION_DELAY = 60
SYSTEM_SHUTDOWN_DELAY = 3600 # 1 h  set to None to disable auto shutdown
WIFI_SHUTDOWN_DELAY = 300 # 5 min       set to None to disable Wifi control

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
GPIO.setup(PIN_CARON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Init GPS interface
gps = GpsPoller()
gps.start()

# Init WiFi control
wifi = WiFiCtrl()

# Init some variables
main_running = True
last_charging = time()
last_charging_soc = 0
last_data = time()
last_evn_transmit = time()
last_evn_settings_poll = time()

# Init SOC notifications
chargingStartSOC = 0
socThreshold = int(config['socThreshold']) if 'socThreshold' in config else 0
abrpSocThreshold = None
notificationSent = False
abortNotificationSent = False
currentSOC = None
print("Notification threshold: {}".format(socThreshold))

# Set up signal handling
def exit_gracefully(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)

try:
    while main_running:
        now = time()
        try:
            data = car.getData()
            fix = gps.fix()
            last_data = now
            is_charging = False

            if fix and fix.mode > 1:
                location = {
                        'latitude':  fix.latitude,
                        'longitude': fix.longitude,
                        'gps_speed': fix.speed
                        }
                if fix.mode > 2:
                    location['altitude'] = fix.altitude
            else:
                location = None

            try:
                if now - last_evn_transmit > EVN_DELAY:
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

                            except EVNotify.CommunicationError:
                                pass

                        # track charging started
                        if is_charging and chargingStartSOC == 0:
                            chargingStartSOC = currentSOC or 0
                        # check if notification threshold reached
                        #elif is_charging and chargingStartSOC < socThreshold and \
                        #        currentSOC >= socThreshold and not notificationSent:
                        #    print("Notification threshold reached")
                        #    EVNotify.sendNotification()
                        #    notificationSent = True
                        elif not is_connected:   # Rearm notification
                            chargingStartSOC = 0
                            notificationSent = False
                            abortNotificationSent = False

                    if location:
                        EVNotify.setLocation({'location': location})

                if is_charging and \
                        last_charging_soc < socThreshold and \
                        currentSOC >= socThreshold:
                    EVNotify.sendNotification()

            except EVNotify.CommunicationError as e:
                print(e)
            except:
                raise

            if 'EXTENDED' in data and is_charging:
                last_charging_soc = currentSOC

        except DONGLE.CAN_ERROR as e:
            print(e)
        except DONGLE.NO_DATA:
            print("NO DATA")
        except CAR.LOW_VOLTAGE as e:
            print("Low Voltage ({})".format(e))
        except CAR.NULL_BLOCK as e:
            print(e)
        except:
            raise
        finally:
            try:
                if not abortNotificationSent \
                        and now - last_charging > ABORT_NOTIFICATION_DELAY \
                        and chargingStartSOC > 0 and last_charging_soc < socThreshold:
                    print("No response detected, send abort notification")
                    EVNotify.sendNotification(True)
                    abortNotificationSent = True

            except EVNotify.CommunicationError as e:
                print("Sending of notificatin failed! {}".format(e))

            if SYSTEM_SHUTDOWN_DELAY != None:
                if now - last_data > SYSTEM_SHUTDOWN_DELAY and GPIO.input(PIN_CARON) == 1:
                    usercnt = int(check_output(['who','-q']).split(b'\n')[1].split(b'=')[1])
                    if usercnt == 0:
                        print("Not charging and car off => Shutdown")
                        check_call(['/bin/systemctl','poweroff'])
                        sleep(5)
                    else:
                        print("Not charging and car off; Not shutting down, users connected")

            if WIFI_SHUTDOWN_DELAY != None:
                if now - last_data > WIFI_SHUTDOWN_DELAY and GPIO.input(PIN_CARON) == 1:
                    if wifi.state == True:
                        print("Disable WiFi")
                        wifi.disable()
                else:
                    if wifi.state == False:
                        print("Enable Wifi")
                        wifi.enable()

            sys.stdout.flush()

            if main_running:
                s = 1 - (time()-now)
                print("sleep({})".format(s))
                if s > 0: sleep(s)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
except:
    raise
finally:
    print("Exiting ...")
    GPIO.cleanup()
    gps.stop()
    print("Bye.")

