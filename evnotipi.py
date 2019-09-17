#!/usr/bin/env python3

from gpspoller import GpsPoller
from subprocess import check_call, check_output
from time import sleep,time
import os
import sys
import signal
import sdnotify
import logging
import evnotify

SYSTEM_SHUTDOWN_DELAY = 900 # 15 min    set to None to disable auto shutdown
WIFI_SHUTDOWN_DELAY = 300 # 5 min       set to None to disable Wifi control

Systemd = sdnotify.SystemdNotifier()

# load config
if os.path.exists('config.json'):
    import json
    with open('config.json', encoding='utf-8') as config_file:
        config = json.loads(config_file.read())
elif os.path.exists('config.yaml'):
    import yaml
    with open('config.yaml', encoding='utf-8') as config_file:
        config = yaml.load(config_file, Loader=yaml.SafeLoader)
else:
    raise Exception('No config found')

logging.basicConfig(level=config['loglevel'] if 'loglevel' in config else logging.INFO)
log = logging.getLogger("EVNotiPi")

# Load OBD2 interface module
if not "{}.py".format(config['dongle']['type']) in os.listdir('dongles'):
    raise Exception('Unsupported dongle {}'.format(config['dongle']['type']))

# Init ODB2 adapter
sys.path.insert(0, 'dongles')
exec("from {0} import {0} as DONGLE".format(config['dongle']['type']))
sys.path.remove('dongles')

if not "{}.py".format(config['car']['type']) in os.listdir('cars'):
    raise Exception('Unsupported car {}'.format(config['car']['type']))

sys.path.insert(0, 'cars')
exec("from {0} import {0} as CAR".format(config['car']['type']))
sys.path.remove('cars')


Threads = []

if 'watchdog' in config and config['watchdog']['enable'] == True:
    import watchdog
    Watchdog = watchdog.Watchdog(config['watchdog'])
else:
    Watchdog = None

dongle = DONGLE(config['dongle'], watchdog = Watchdog)
car = CAR(config['car'], dongle)
Threads.append(car)

# Init GPS interface
gps = GpsPoller()
Threads.append(gps)

# Init EVNotify
EVNotify = evnotify.EVNotify(config['evnotify'], car, gps)
Threads.append(EVNotify)

# Init WiFi control
if 'wifi' in config and config['wifi']['enable'] == True:
    from wifi_ctrl import WiFiCtrl
    wifi = WiFiCtrl()
else:
    wifi = None

# Init some variables
main_running = True

# Set up signal handling
def exit_gracefully(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, exit_gracefully)

# Start polling loops
for t in Threads:
    t.start()

Systemd.notify("READY=1")
log.info("Starting main loop")
try:
    while main_running:
        now = time()
        watchdogs_ok = True
        for t in Threads:
            if t.checkWatchdog() == False:
                log.error("Watchdog Failed " + str(t))
                watchdogs_ok = False

        if watchdogs_ok:
            Systemd.notify("WATCHDOG=1")

        if SYSTEM_SHUTDOWN_DELAY != None:
            if now - car.last_data > SYSTEM_SHUTDOWN_DELAY and dongle.isCarAvailable() == False:
                usercnt = int(check_output(['who','-q']).split(b'\n')[1].split(b'=')[1])
                if usercnt == 0:
                    log.info("Not charging and car off => Shutdown")
                    check_call(['/bin/systemctl','poweroff'])
                    sleep(5)
                else:
                    log.info("Not charging and car off; Not shutting down, users connected")

        if wifi and WIFI_SHUTDOWN_DELAY != None:
            if now - car.last_data > WIFI_SHUTDOWN_DELAY and dongle.isCarAvailable() == False:
                wifi.disable()
            else:
                wifi.enable()

        sys.stdout.flush()

        if main_running:
            loop_delay = 1 - (time()-now)
            if loop_delay > 0: sleep(loop_delay)

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
    Systemd.notify("STOPPING=1")
finally:
    Systemd.notify("STOPPING=1")
    log.info("Exiting ...")
    for t in Threads[::-1]: # reverse Threads
        t.stop()
    log.info("Bye.")

