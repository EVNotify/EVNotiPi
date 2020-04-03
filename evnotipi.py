#!/usr/bin/env python3

from gevent.monkey import patch_all; patch_all()
from subprocess import check_call, check_output
from time import sleep, time
from argparse import ArgumentParser
import os
import sys
import signal
import logging
import sdnotify
import evnotify
from gpspoller import GpsPoller
import car
import dongle

# Exit signalhandler
def exit_gracefully(signum, frame):
    sys.exit(0)

Systemd = sdnotify.SystemdNotifier()

class WatchdogFailure(Exception): pass

parser = ArgumentParser(description='EVNotiPi')
parser.add_argument('-d', '--debug', dest='debug',
                    action='store_true', default=False)
parser.add_argument('-c', '--config', dest='config',
                    action='store', default='config.yaml')
args = parser.parse_args()
del parser

# load config
if os.path.exists(args.config):
    if args.config[-5:] == '.json':
        import json
        with open(args.config, encoding='utf-8') as config_file:
            config = json.loads(config_file.read())
    elif args.config[-5:] == '.yaml':
        import yaml
        with open(args.config, encoding='utf-8') as config_file:
            config = None
            # use the last document in config.yaml as config
            for c in yaml.load_all(config_file, Loader=yaml.SafeLoader):
                config = c
    else:
        raise Exception('Unknown config type')
else:
    raise Exception('No config found')

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
elif 'loglevel' in config:
    logging.basicConfig(level=config['loglevel'])
else:
    logging.basicConfig(level=logging.INFO)
log = logging.getLogger("EVNotiPi")

del args

# Load OBD2 interface module
DONGLE = dongle.Load(config['dongle']['type'])

# Load car module
CAR = car.Load(config['car']['type'])

Threads = []

if 'watchdog' in config and config['watchdog'].get('enable') is True:
    import watchdog
    Watchdog = watchdog.Watchdog(config['watchdog'])
else:
    Watchdog = None

# Init dongle
dongle = DONGLE(config['dongle'], watchdog=Watchdog)

# Init GPS interface
gps = GpsPoller()
Threads.append(gps)

# Init car
car = CAR(config['car'], dongle, gps)
Threads.append(car)

# Init EVNotify
EVNotify = evnotify.EVNotify(config['evnotify'], car)
Threads.append(EVNotify)

# Init WiFi control
if 'wifi' in config and config['wifi'].get('enable') is True:
    from wifi_ctrl import WiFiCtrl
    wifi = WiFiCtrl()
else:
    wifi = None

# Init some variables
main_running = True

# Set up signal handling
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
            status = t.checkWatchdog()
            if not status:
                log.error("Watchdog Failed %s", str(t))
                watchdogs_ok = False
                raise WatchdogFailure(str(t))

        if watchdogs_ok:
            Systemd.notify("WATCHDOG=1")

        if 'system' in config and 'shutdown_delay' in config['system']:
            if (now - car.last_data > config['system']['shutdown_delay'] and
                    not dongle.isCarAvailable()):
                user_cnt = int(check_output(['who', '-q']).split(b'\n')[1].split(b'=')[1])
                if user_cnt == 0:
                    log.info("Not charging and car off => Shutdown")
                    check_call(['/bin/systemctl', 'poweroff'])
                    sleep(5)
                else:
                    log.info("Not charging and car off; Not shutting down, users connected")

        if wifi and config['wifi']['shutdown_delay'] is not None:
            if (now - car.last_data > config['wifi']['shutdown_delay'] and
                    not dongle.isCarAvailable()):
                wifi.disable()
            else:
                wifi.enable()

        sys.stdout.flush()

        if main_running:
            loop_delay = 1 - (time()-now)
            sleep(max(0, loop_delay))

except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
    main_running = False
    Systemd.notify("STOPPING=1")
finally:
    Systemd.notify("STOPPING=1")
    log.info("Exiting ...")
    for t in Threads[::-1]: # reverse Threads
        t.stop()
    log.info("Bye.")
