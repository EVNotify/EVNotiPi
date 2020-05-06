from time import time
from .car import *

CMD_AUX_VOLTAGE  = bytes.fromhex('222005')  # EVC
CMD_CHARGE_STATE = bytes.fromhex('225017')  # BCB 0:Nok;1:AC mono;2:AC tri;3:DC;4:AC bi
CMD_SOC          = bytes.fromhex('222002')  # EVC
CMD_SOC_BMS      = bytes.fromhex('229002')  # LBC
CMD_VOLTAGE      = bytes.fromhex('223203')  # LBC
CMD_BMS_ENERGY   = bytes.fromhex('2291C8')  # PR155
CMD_ODO          = bytes.fromhex('222006')  # EVC
CMD_NRG_DISCHARG = bytes.fromhex('229245')  # PR047
CMD_CURRENT      = bytes.fromhex('223204')  # EVC
CMD_SOH          = bytes.fromhex('223206')  # EVC

class ZOE_ZE50(Car):
    def __init__(self, config, dongle, gps):
        Car.__init__(self, config, dongle, gps)
        self.dongle.setProtocol('CAN_29_500')

    def readDongle(self, data):
        def lbc(cmd):   # Lithium Battery Controller
            return self.dongle.sendCommandEx(cmd, canrx=0x18daf1db, cantx=0x18dadbf1)[3:]
        def evc(cmd):   # Vehicle Controle Module
            return self.dongle.sendCommandEx(cmd, canrx=0x18daf1da, cantx=0x18dadaf1)[3:]
        def bcb(cmd):   # Battery Charger Block
            return self.dongle.sendCommandEx(cmd, canrx=0x18daf1de, cantx=0x18dadef1)[3:]

        data.update(self.getBaseData())

        dc_battery_current = (ifbu(evc(CMD_CURRENT)) - 32768) / 4
        dc_battery_voltage = ifbu(evc(CMD_VOLTAGE)) / 2

        cellVolts = []
        for i in range(0x21, 0x84):
            c = bytes.fromhex("2290{:02x}".format(i))
            cellVolts.append(ifbu(lbc(c)) / 1000)

        moduleTemps = []
        for i in range(0x31, 0x3d):
            c = bytes.fromhex("2291{:02x}".format(i))
            moduleTemps.append(ifbu(lbc(c)) / 10 - 60)

        charge_state = ifbu(bcb(CMD_CHARGE_STATE))

        data.update({
            #Base
            'SOC_BMS':              ifbu(lbc(CMD_SOC_BMS)) / 100.0,
            'SOC_DISPLAY':          ifbu(evc(CMD_SOC)) / 50.0,

            #Extended:
            'auxBatteryVoltage':    ifbu(evc(CMD_AUX_VOLTAGE)) / 100.0,

            #'batteryInletTemperature':
            'batteryMaxTemperature': max(moduleTemps),
            'batteryMinTemperature': min(moduleTemps),

            'cumulativeEnergyCharged':  ifbu(lbc(CMD_BMS_ENERGY)) / 1000.0,
            'cumulativeEnergyDischarged': ifbu(lbc(CMD_NRG_DISCHARG)) / 1000.0,

            'charging':             int(charge_state != 0),
            'normalChargePort':     int(charge_state in (1,2,4))
            'rapidChargePort':      int(charge_state == 3)

            'dcBatteryCurrent':     dc_battery_current,
            'dcBatteryPower':       dc_battery_current * dc_battery_voltage / 1000.0,
            'dcBatteryVoltage':     dc_battery_voltage,

            'soh':                  ifbu(evc(CMD_SOH)),
            #'externalTemperature':
            'odo':                  ifbu(evc(CMD_ODO)),
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
