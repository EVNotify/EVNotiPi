from car import *
from dongle import NoData
from time import time

b2101 = bytes.fromhex('2101')
b2102 = bytes.fromhex('2102')
b2103 = bytes.fromhex('2103')
b2104 = bytes.fromhex('2104')
b2105 = bytes.fromhex('2105')
b2180 = bytes.fromhex('2180')
b22b002 = bytes.fromhex('22b002')

class IONIQ_BEV(Car):

    def __init__(self, config, dongle, gps):
        Car.__init__(self, config, dongle, gps)
        self.dongle.setProtocol('CAN_11_500')

    def readDongle(self, data):
        now = time()
        raw = {}

        for cmd in [b2101,b2102,b2103,b2104,b2105]:
            raw[cmd] = self.dongle.sendCommandEx(cmd, canrx=0x7ec, cantx=0x7e4)

        raw[b2180] = self.dongle.sendCommandEx(b2180, canrx=0x7ee, cantx=0x7e6)

        try:
            raw[b22b002] = self.dongle.sendCommandEx(b22b002, canrx=0x7ce, cantx=0x7c6)
        except NoData:
            # 0x7ce is only available while driving
            pass

        data.update(self.getBaseData())

        chargingBits = raw[b2101][11]
        dcBatteryCurrent = ifbs(raw[b2101][12:14]) / 10.0
        dcBatteryVoltage = ifbu(raw[b2101][14:16]) / 10.0

        cellTemps = [
                ifbs(raw[b2101][18:19]), #  0
                ifbs(raw[b2101][19:20]), #  1
                ifbs(raw[b2101][20:21]), #  2
                ifbs(raw[b2101][21:22]), #  3
                ifbs(raw[b2101][22:23]), #  4
                ifbs(raw[b2105][11:12]), #  5
                ifbs(raw[b2105][12:13]), #  6
                ifbs(raw[b2105][13:14]), #  7
                ifbs(raw[b2105][14:15]), #  8
                ifbs(raw[b2105][15:16]), #  9
                ifbs(raw[b2105][16:17]), # 10
                ifbs(raw[b2105][17:18])] # 11

        cellVoltages = []
        for cmd in [b2102, b2103, b2104]:
            for byte in range(6,38):
                cellVoltages.append(raw[cmd][byte] / 50.0)

        data.update({
            # Base:
            'SOC_BMS':                  raw[b2101][6] / 2.0,
            'SOC_DISPLAY':              raw[b2105][33] / 2.0,

            # Extended:
            'auxBatteryVoltage':        raw[b2101][31] / 10.0,

            'batteryInletTemperature':  ifbs(raw[b2101][22:23]),
            'batteryMaxTemperature':    ifbs(raw[b2101][16:17]),
            'batteryMinTemperature':    ifbs(raw[b2101][17:18]),

            'cumulativeEnergyCharged':  ifbu(raw[b2101][40:44]) / 10.0,
            'cumulativeEnergyDischarged': ifbu(raw[b2101][44:48]) / 10.0,

            'charging':                 1 if chargingBits & 0x80 else 0,
            'normalChargePort':         1 if chargingBits & 0x20 else 0,
            'rapidChargePort':          1 if chargingBits & 0x40 else 0,

            'dcBatteryCurrent':         dcBatteryCurrent,
            'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
            'dcBatteryVoltage':         dcBatteryVoltage,

            'soh':                      ifbu(raw[b2105][27:29]) / 10.0,
            'externalTemperature':      (raw[b2180][14] - 80) / 2.0,
            'odo':                      ffbu(raw[b22b002][9:12]) if b22b002 in raw else None,

            # Additional:
            'cumulativeChargeCurrent':  ifbu(raw[b2101][32:36]) / 10.0,
            'cumulativeDischargeCurrent': ifbu(raw[b2101][36:40]) / 10.0,

            'batteryAvgTemperature':    sum(cellTemps) / len(cellTemps),
            'driveMotorSpeed':          ifbs(raw[b2101][55:57]),

            'fanStatus':                raw[b2101][29],
            'fanFeedback':              raw[b2101][30],

            'availableChargePower':     ifbu(raw[b2101][7:9]) / 100.0,
            'availableDischargePower':  ifbu(raw[b2101][9:11]) / 100.0,

            'obdVoltage':               self.dongle.getObdVoltage(),
            })

        for i,temp in enumerate(cellTemps):
            key = "cellTemp{:02d}".format(i+1)
            data[key] = float(temp)

        for i,cvolt in enumerate(cellVoltages):
            key = "cellVoltage{:02d}".format(i+1)
            data[key] = float(cvolt)

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def getABRPModel(self): return 'hyundai:ioniq:17:28:other'

    def getEVNModel(self): return 'IONIQ_BEV'

