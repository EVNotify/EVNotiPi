#!/usr/bin/env python3
""" EVNotiPi main module """

from gevent.monkey import patch_all; patch_all()
import logging
import os
import signal
import sys
from argparse import ArgumentParser
from subprocess import check_call, check_output
from time import sleep, time
import sdnotify
from gpspoller import GpsPoller
import evnotify
import car
import dongle
import watchdog

Systemd = sdnotify.SystemdNotifier()


class ThreadFailure(Exception):
    """ Raised when a sub thread fails """


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

# emulate old config if watchdog section is missing
if 'watchdog' not in config or 'type' not in config['watchdog']:
    log.warning('Old watchdog config syntax detected. Please adjust according to config.yaml.template.')
    config['watchdog'] = {
        'type': 'GPIO',
        'shutdown_pin': config['dongle'].get('shutdown_pin', 24),
        'pup_down': config['dongle'].get('pup_down', 21),
    }

# Load OBD2 interface module
DONGLE = dongle.load(config['dongle']['type'])

# Load car module
CAR = car.load(config['car']['type'])

# Load watchdog module
WATCHDOG = watchdog.load(config['watchdog']['type'])

Threads = []

# Init watchdog
watchdog = WATCHDOG(config['watchdog'])

# Init dongle
dongle = DONGLE(config['dongle'])

# Init GPS interface
gps = GpsPoller()
Threads.append(gps)

# Init car
car = CAR(config['car'], dongle, watchdog, gps)
Threads.append(car)

# Init EVNotify
EVNotify = evnotify.EVNotify(config['evnotify'], car)
Threads.append(EVNotify)


# Set up signal handling
def exit_gracefully(signum, frame):
    """ Signalhandler for SIGTERM """
    sys.exit(0)


signal.signal(signal.SIGTERM, exit_gracefully)

# Start polling loops
for t in Threads:
    t.start()

Systemd.notify('READY=1')
log.info('Starting main loop')

# Suppress duplicate logs
LOG_USER = 1
log_flags = 0

main_running = True
try:
    while main_running:
        now = time()
        threads_ok = True
        for t in Threads:
            status = t.check_thread()
            if not status:
                log.error('Thread Failed (%s)', str(t))
                threads_ok = False
                raise ThreadFailure(str(t))

        if threads_ok:
            Systemd.notify('WATCHDOG=1')

        if 'system' in config and 'shutdown_delay' in config['system']:
            if (now - car.last_data > config['system']['shutdown_delay'] and
                    not watchdog.is_car_available()):
                usercnt = int(check_output(['who', '-q']).split(b'\n')[1].split(b'=')[1])
                if usercnt == 0:
                    log.info('Not charging and car off => Shutdown')
                    check_call(['/bin/systemctl', 'poweroff'])
                    sleep(5)
                elif not log_flags & LOG_USER:
                    log.info('Not charging and car off; Not shutting down, users connected')
                    log_flags |= LOG_USER
            elif log_flags & LOG_USER:
                log_flags &= ~LOG_USER

        # Ensure messages get printed to the console.
        sys.stdout.flush()

        if main_running:
            loop_delay = 1 - (time()-now)
            sleep(max(0, loop_delay))

except (KeyboardInterrupt, SystemExit):  # when you press ctrl+c
    main_running = False
    Systemd.notify('STOPPING=1')
finally:
    Systemd.notify('STOPPING=1')
    log.info('Exiting ...')
    for t in Threads[::-1]:  # reverse Threads
        t.stop()
    log.info('Bye.')
