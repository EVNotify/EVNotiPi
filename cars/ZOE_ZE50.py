from car import *
from time import time

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

class IONIQ_BEV(Car):

    def __init__(self, config, dongle):
        Car.__init__(self, config, dongle)
        self.dongle.setProtocol('CAN_11_500')

    def readDongle(self):
        now = time()
        raw = {}

        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCanID(0x7e4)
        for cmd in [b19023b]:
            raw[cmd] = self.dongle.sendCommandEx(cmd, cantx=0x18DAF1DE, canrx=0x18DADEF1)

        data = self.getBaseData()

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 50,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 50.0
        }

