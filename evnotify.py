#!/usr/bin/env python3

import re
import time
import string
import io
import json
#import importlib
import sys
from time import sleep

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

dongle = DONGLE(config['dongle'])

# Init car interface
cartype = EVNotify.getSettings()['car']
if cartype == 'IONIQ_BEV':
    from IONIQ_BEV import IONIQ_BEV as CAR
elif cartype == 'KONA_EV':
    from KONA_EV import KONA_BEV as CAR

car = CAR(dongle)


while True:
    data = car.getData()
    print(data)
    EVNotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])
    EVNotify.setExtended(data['EXTENDED'])
    sleep(2)

