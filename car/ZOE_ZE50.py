from time import time
from .car import *

CMD_AUX_VOLTAGE  = bytes.fromhex('222005')   # PR252
CMD_CHARGE_STATE = bytes.fromhex('225017')   # ET018
CMD_SOC          = bytes.fromhex('229001')
CMD_SOC_BMS      = bytes.fromhex('229002')
CMD_VOLTAGE      = bytes.fromhex('229006')
CMD_BMS_ENERGY   = bytes.fromhex('2291C8')   # PR155
CMD_ODO          = bytes.fromhex('2291CF')   # PR046 ?? 0x80000225 => 17km ?
CMD_NRG_DISCHARG = bytes.fromhex('229245')   # PR047
CMD_CURRENT      = bytes.fromhex('229257')   # PR218
CMD_SOH          = bytes.fromhex('22927A')   # ET148

class ZOE_ZE50(Car):
    def __init__(self, config, dongle, gps):
        Car.__init__(self, config, dongle, gps)
        self.dongle.setProtocol('CAN_29_500')

    def readDongle(self, data):
        def bms(cmd):
            return self.dongle.sendCommandEx(cmd, canrx=0x18DAF1DB, cantx=0x18DADBF1)[3:]

        data.update(self.getBaseData())

        dc_battery_current = ifbu(bms(CMD_CURRENT)) - 32768
        dc_battery_voltage = ifbu(bms(CMD_VOLTAGE)) / 1000

        #soh_raw = bms(CMD_SOH) # returns 254 bytes of data ...

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
            'SOC_BMS':              ifbu(bms(CMD_SOC_BMS)) / 100,
            'SOC_DISPLAY':          ifbu(bms(CMD_SOC)) / 100,

            #Extended:
            'auxBatteryVoltage':    ifbu(bms(CMD_AUX_VOLTAGE)) / 100.0,

            #'batteryInletTemperature':
            'batteryMaxTemperature': max(moduleTemps),
            'batteryMinTemperature': min(moduleTemps),

            'cumulativeEnergyCharged':  ifbu(bms(CMD_BMS_ENERGY)) / 1000.0,
            'cumulativeEnergyDischarged': ifbu(bms(CMD_NRG_DISCHARG)) / 1000.0,

            'charging':             0 if ifbu(bms(CMD_CHARGE_STATE)) == 0 else 1,
            #'normalChargePort':
            #'rapidChargePort':

            'dcBatteryCurrent':     dc_battery_current,
            'dcBatteryPower':       dc_battery_current * dc_battery_voltage / 1000.0,
            'dcBatteryVoltage':     dc_battery_voltage,

            #'soh':
            #'externalTemperature':
            #'odo':                  ifbu(bms(CMD_ODO)),
            })

        for i, cvolt in enumerate(cellVolts):
            key = "cellVoltage{:02d}".format(i+1)
            data[key] = float(cvolt)

        for i, temp in enumerate(moduleTemps):
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

    from ..dongle.SocketCAN import SocketCAN

    config = {
        'type': 'SocketCAN',
        'port': 'vcan0',
        'speed': 500000,
        }

    dongle = SocketCAN(config, watchdog=None)

    car = ZOE_ZE50({'interval': 1}, dongle)

    data = {}
    car.readDongle(data)
    pp.pprint(data)
