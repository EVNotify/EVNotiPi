if __name__ == '__main__':
    import sys
    sys.path.insert(0,'.')
from car import *
from time import time

cmd_auxVoltage  = bytes.fromhex('222005')   # PR252
cmd_chargeState = bytes.fromhex('225017')   # ET018
cmd_soc         = bytes.fromhex('229001')
cmd_soc_bms     = bytes.fromhex('229002')
cmd_voltage     = bytes.fromhex('229006')
cmd_bms_energy  = bytes.fromhex('2291C8')   # PR155
cmd_odo         = bytes.fromhex('2291CF')   # PR046 ?? 0x80000225 => 17km ?
cmd_nrg_discharg= bytes.fromhex('229245')   # PR047
cmd_current     = bytes.fromhex('229257')   # PR218
cmd_soh         = bytes.fromhex('22927A')   # ET148

class ZOE_ZE50(Car):
    def __init__(self, config, dongle, gps):
        Car.__init__(self, config, dongle, gps)
        self.dongle.setProtocol('CAN_29_500')

    def readDongle(self, data):
        def bms(cmd):
            return self.dongle.sendCommandEx(cmd, canrx=0x18DAF1DB, cantx=0x18DADBF1)[3:]

        data.update(self.getBaseData())

        dcBatteryCurrent = ifbu(bms(cmd_current)) - 32768
        dcBatteryVoltage = ifbu(bms(cmd_voltage)) / 1000

        #soh_raw = bms(cmd_soh) # returns 254 bytes of data ...

        cellVolts = []
        for i in range(0x21, 0x84):
            c = bytes.fromhex("2290{:02x}".format(i))
            cellVolts.append(ifbu(bms(c)) / 1000)

        moduleTemps = []
        for i in range(0x31, 0x3d):
            c = bytes.fromhex("2291{:02x}".format(i))
            moduleTemps.append(ifbu(bms(c)) / 10 - 60)

        data.update({
            #Base
            'SOC_BMS':              ifbu(bms(cmd_soc_bms)) / 100
            'SOC_DISPLAY':          ifbu(bms(cmd_soc)) / 100

            #Extended:
            'auxBatteryVoltage':    ifbu(bms(cmd_auxVoltage)) / 100.0,

            #'batteryInletTemperature':
            'batteryMaxTemperature': max(moduleTemps),
            'batteryMinTemperature': min(moduleTemps),

            'cumulativeEnergyCharged':  ifbu(bms(cmd_bms_energy)) / 1000.0,
            'cumulativeEnergyDischarged': ifbu(bms(cmd_nrg_discharg)) / 1000.0,

            'charging':             0 if ifbu(bms(cmd_chargeState)) == 0 else 1,
            #'normalChargePort':
            #'rapidChargePort':

            'dcBatteryCurrent':     dcBatteryCurrent,
            'dcBatteryPower':       dcBatteryCurrent * dcBatteryVoltage / 1000.0,
            'dcBatteryVoltage':     dcBatteryVoltage,

            #'soh':
            #'externalTemperature':
            #'odo':                  ifbu(bms(cmd_odo)),
            })

        for i,cvolt in enumerate(cellVolts):
            key = "cellVoltage{:02d}".format(i+1)
            data[key] = float(cvolt)

        for i,temp in enumerate(moduleTemps):
            key = "cellTemp{:02d}".format(i+1)
            data[key] = float(temp)

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

    data = {}
    car.readDongle(data)
    pp.pprint(data)

