#!/usr/bin/python3

import sys
import logging
from binascii import hexlify
import pprint
pp = pprint.PrettyPrinter(indent=2)

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, 'dongles')
from SocketCAN import SocketCAN
sys.path.insert(0, 'cars')
import ZOE_ZE50

config = {
        'type': 'SocketCAN',
        'port': 'vcan0',
        'speed': 500000,
        }

dongle = SocketCAN(config, watchdog=None)

car = ZOE_ZE50.ZOE_ZE50({'interval': 1}, dongle)

pp.pprint(car.readDongle())

