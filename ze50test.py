#!/usr/bin/python3

import sys
from binascii import hexlify

sys.path.insert(0, 'dongles')
import SocketCAN from SocketCAN

config = {
        'type': 'SocketCAN',
        'port': 'can0',
        'speed': 500000
        }

dongle = SocketCAN(config, Watchdog=None)

b19023b = bytes.fromhex('19023b')
b222001 = bytes.fromhex('222001')
b222002 = bytes.fromhex('222002')
b222003 = bytes.fromhex('222003')
b222004 = bytes.fromhex('222004')
b222005 = bytes.fromhex('222005')

b22500d = bytes.fromhex('22500d')
b225017 = bytes.fromhex('225017')
b225026 = bytes.fromhex('225026')
b225027 = bytes.fromhex('225027')

b22503a = bytes.fromhex('22503a')
b22503b = bytes.fromhex('22503b')
b22503f = bytes.fromhex('22503f')

b225041 = bytes.fromhex('225041')
b225042 = bytes.fromhex('225042')
b22504a = bytes.fromhex('22504a')

b225054 = bytes.fromhex('225054')
b225057 = bytes.fromhex('225057')
b225058 = bytes.fromhex('225058')
b225059 = bytes.fromhex('225059')
b22505a = bytes.fromhex('22505a')

b225062 = bytes.fromhex('225062')
b225064 = bytes.fromhex('225064')

data = dongle.sendCommandEx(b19023b, cantx=0x18DAF1DE, canrx=0x18DADEF1)

print(hexlify(data))
