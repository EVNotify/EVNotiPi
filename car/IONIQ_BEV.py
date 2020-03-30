from time import time
from dongle.dongle import NoData
from .car import *

B2101 = bytes.fromhex('2101')
B2102 = bytes.fromhex('2102')
B2103 = bytes.fromhex('2103')
B2104 = bytes.fromhex('2104')
B2105 = bytes.fromhex('2105')
B2180 = bytes.fromhex('2180')
B22b002 = bytes.fromhex('22b002')

class IONIQ_BEV(Car):

    def __init__(self, config, dongle, gps):
        Car.__init__(self, config, dongle, gps)
        self.dongle.setProtocol('CAN_11_500')

    def readDongle(self, data):
        now = time()
        raw = {}

        for cmd in [B2101, B2102, B2103, B2104, B2105]:
            raw[cmd] = self.dongle.sendCommandEx(cmd, canrx=0x7ec, cantx=0x7e4)

        raw[B2180] = self.dongle.sendCommandEx(B2180, canrx=0x7ee, cantx=0x7e6)

        try:
            raw[B22b002] = self.dongle.sendCommandEx(B22b002, canrx=0x7ce, cantx=0x7c6)
        except NoData:
            # 0x7ce is only available while driving
            pass

        data.update(self.getBaseData())

        charging_bits = raw[B2101][11]
        dc_battery_current = ifbs(raw[B2101][12:14]) / 10.0
        dc_battery_voltage = ifbu(raw[B2101][14:16]) / 10.0

        cell_temps = [
            ifbs(raw[B2101][18:19]), #  0
            ifbs(raw[B2101][19:20]), #  1
            ifbs(raw[B2101][20:21]), #  2
            ifbs(raw[B2101][21:22]), #  3
            ifbs(raw[B2101][22:23]), #  4
            ifbs(raw[B2105][11:12]), #  5
            ifbs(raw[B2105][12:13]), #  6
            ifbs(raw[B2105][13:14]), #  7
            ifbs(raw[B2105][14:15]), #  8
            ifbs(raw[B2105][15:16]), #  9
            ifbs(raw[B2105][16:17]), # 10
            ifbs(raw[B2105][17:18])] # 11

        cell_voltages = []
        for cmd in [B2102, B2103, B2104]:
            for byte in range(6, 38):
                cell_voltages.append(raw[cmd][byte] / 50.0)

        data.update({
            # Base:
            'SOC_BMS':                  raw[B2101][6] / 2.0,
            'SOC_DISPLAY':              raw[B2105][33] / 2.0,

            # Extended:
            'auxBatteryVoltage':        raw[B2101][31] / 10.0,

            'batteryInletTemperature':  ifbs(raw[B2101][22:23]),
            'batteryMaxTemperature':    ifbs(raw[B2101][16:17]),
            'batteryMinTemperature':    ifbs(raw[B2101][17:18]),

            'cumulativeEnergyCharged':  ifbu(raw[B2101][40:44]) / 10.0,
            'cumulativeEnergyDischarged': ifbu(raw[B2101][44:48]) / 10.0,

            'charging':                 1 if charging_bits & 0x80 else 0,
            'normalChargePort':         1 if charging_bits & 0x20 else 0,
            'rapidChargePort':          1 if charging_bits & 0x40 else 0,

            'dcBatteryCurrent':         dc_battery_current,
            'dcBatteryPower':           dc_battery_current * dc_battery_voltage / 1000.0,
            'dcBatteryVoltage':         dc_battery_voltage,

            'soh':                      ifbu(raw[B2105][27:29]) / 10.0,
            'externalTemperature':      (raw[B2180][14] - 80) / 2.0,
            'odo':                      ffbu(raw[B22b002][9:12]) if B22b002 in raw else None,

            # Additional:
            'cumulativeChargeCurrent':  ifbu(raw[B2101][32:36]) / 10.0,
            'cumulativeDischargeCurrent': ifbu(raw[B2101][36:40]) / 10.0,

            'batteryAvgTemperature':    sum(cell_temps) / len(cell_temps),
            'driveMotorSpeed':          ifbs(raw[B2101][55:57]),

            'fanStatus':                raw[B2101][29],
            'fanFeedback':              raw[B2101][30],

            'availableChargePower':     ifbu(raw[B2101][7:9]) / 100.0,
            'availableDischargePower':  ifbu(raw[B2101][9:11]) / 100.0,

            'obdVoltage':               self.dongle.getObdVoltage(),
            })

        for i, temp in enumerate(cell_temps):
            key = "cellTemp{:02d}".format(i+1)
            data[key] = float(temp)

        for i, cvolt in enumerate(cell_voltages):
            key = "cellVoltage{:02d}".format(i+1)
            data[key] = float(cvolt)

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def getABRPModel(self):
        return 'hyundai:ioniq:17:28:other'

    def getEVNModel(self):
        return 'IONIQ_BEV'
