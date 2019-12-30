if __name__ == '__main__':
    import sys
    sys.path.insert(0,'.')
from car import *
from time import time

cmd_soc     = bytes.fromhex('229002')
cmd_voltage = bytes.fromhex('229006')
cmd_current = bytes.fromhex('229257')

class ZOE_ZE50(Car):

    def __init__(self, config, dongle):
        Car.__init__(self, config, dongle)
        self.dongle.setProtocol('CAN_29_500')

    def readDongle(self):
        def bms(cmd):
            return self.dongle.sendCommandEx(cmd, canrx=0x18DAF1DB, cantx=0x18DADBF1)

        now = time()

        data = self.getBaseData()

        data['timestamp']   = now
        data['SOC_BMS']     = ifbu(bms(cmd_soc)[3:]) / 100
        #data['SOC_DISPLAY'] = raw[b2105][0x7ec][4][6] / 2.0

        dcBatteryCurrent = ifbu(bms(cmd_current)[3:]) - 32768
        dcBatteryVoltage = ifbu(bms(cmd_voltage)[3:]) / 1000

        cellVolts = []
        for i in range(0x21, 0x84):
            c = bytes.fromhex("2290{:02x}".format(i))
            cellVolts.append(ifbu(bms(c)[3:]) / 1000)

        moduleTemps = []
        for i in range(0x31, 0x3d):
            c = bytes.fromhex("2291{:02x}".format(i))
            moduleTemps.append(ifbu(bms(c)[3:]) / 10 - 60)

        data['EXTENDED'] = {
                #'auxBatteryVoltage':

                #'batteryInletTemperature':
                'batteryMaxTemperature': max(moduleTemps),
                'batteryMinTemperature': min(moduleTemps),

                #'cumulativeEnergyCharged':
                #'cumulativeEnergyDischarged':

                #'charging':
                #'normalChargePort':
                #'rapidChargePort':

                'dcBatteryCurrent':     dcBatteryCurrent,
                'dcBatteryPower':       dcBatteryCurrent * dcBatteryVoltage / 1000,
                'dcBatteryVoltage':     dcBatteryVoltage,

                #'soh':
                #'externalTemperature':
                #'odo':
                }

        data['ADDITIONAL'] = {
                'obdVoltage':               self.dongle.getObdVoltage(),
                }

        for i,cvolt in enumerate(cellVolts):
            key = "cellVoltage{:02d}".format(i+1)
            data['ADDITIONAL'][key] = float(cvolt)

        for i,temp in enumerate(moduleTemps):
            key = "cellTemp{:02d}".format(i+1)
            data['ADDITIONAL'][key] = float(temp)

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 50,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 50.0
        }


if __name__ == '__main__':
    import sys
    import logging
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

