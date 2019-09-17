from car import *
from time import time

b2101 = bytes.fromhex('2101')
b2102 = bytes.fromhex('2102')
b2103 = bytes.fromhex('2103')
b2104 = bytes.fromhex('2104')
b2105 = bytes.fromhex('2105')
b2180 = bytes.fromhex('2180')
b22b002 = bytes.fromhex('22b002')

class IONIQ_BEV(Car):

    def __init__(self, config, dongle):
        Car.__init__(self, config, dongle)
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCANRxMask(0x7ff)

    def readDongle(self):
        now = time()
        raw = {}

        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCanID(0x7e4)
        for cmd in [b2101,b2102,b2103,b2104,b2105]:
            raw[cmd] = self.dongle.sendCommand(cmd)

        self.dongle.setCANRxFilter(0x7ee)
        self.dongle.setCanID(0x7e6)
        raw[b2180] = self.dongle.sendCommand(b2180)

        if len(raw[b2101][0x7ec]) != 9 or \
                len(raw[b2105][0x7ec]) != 7 or \
                len(raw[b2180][0x7ee]) != 4:
            raise DataError("Got wrong count of frames!\n"+str(raw))

        data = self.getBaseData()

        data['timestamp']   = now
        data['SOC_BMS']     = raw[b2101][0x7ec][1][0] / 2.0
        data['SOC_DISPLAY'] = raw[b2105][0x7ec][4][6] / 2.0

        chargingBits = raw[b2101][0x7ec][1][5]
        dcBatteryCurrent = ifbs(raw[b2101][0x7ec][1][6:7] + raw[b2101][0x7ec][2][0:1]) / 10.0
        dcBatteryVoltage = ifbu(raw[b2101][0x7ec][2][1:3]) / 10.0

        cellTemps = [
                ifbs(raw[b2101][0x7ec][2][5:6]), #  0
                ifbs(raw[b2101][0x7ec][2][6:7]), #  1
                ifbs(raw[b2101][0x7ec][3][0:1]), #  2
                ifbs(raw[b2101][0x7ec][3][1:2]), #  3
                ifbs(raw[b2101][0x7ec][3][2:3]), #  4
                ifbs(raw[b2105][0x7ec][1][5:6]), #  5
                ifbs(raw[b2105][0x7ec][1][6:7]), #  6
                ifbs(raw[b2105][0x7ec][2][0:1]), #  7
                ifbs(raw[b2105][0x7ec][2][1:2]), #  8
                ifbs(raw[b2105][0x7ec][2][2:3]), #  9
                ifbs(raw[b2105][0x7ec][2][3:4]), # 10
                ifbs(raw[b2105][0x7ec][2][4:5])] # 11

        cellVoltages = []
        for cmd in [b2102, b2103, b2104]:
            for cell in range(0,31):
                frame = int(cell / 7) + 1
                byte = int(cell % 7)
                cellVoltages.append(ifbu(raw[cmd][0x7ec][frame][byte:byte+1]) / 50.0)

        data['EXTENDED'] = {
                'auxBatteryVoltage':        raw[b2101][0x7ec][4][4] / 10.0,

                'batteryInletTemperature':  ifbs(raw[b2101][0x7ec][3][2:3]),
                'batteryMaxTemperature':    ifbs(raw[b2101][0x7ec][2][3:4]),
                'batteryMinTemperature':    ifbs(raw[b2101][0x7ec][2][4:5]),

                'cumulativeEnergyCharged':  ifbu(raw[b2101][0x7ec][5][6:7] + raw[b2101][0x7ec][6][0:3]) / 10.0,
                'cumulativeEnergyDischarged': ifbu(raw[b2101][0x7ec][6][3:7]) / 10.0,

                'charging':                 1 if chargingBits & 0x80 else 0,
                'normalChargePort':         1 if chargingBits & 0x20 else 0,
                'rapidChargePort':          1 if chargingBits & 0x40 else 0,

                'dcBatteryCurrent':         dcBatteryCurrent,
                'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
                'dcBatteryVoltage':         dcBatteryVoltage,

                'soh':                      ifbu(raw[b2105][0x7ec][4][0:2]) / 10.0,
                'externalTemperature':      (raw[b2180][0x7ee][2][1] - 80) / 2.0,
                }

        if data['EXTENDED']['charging'] == 0:
            self.dongle.setCANRxFilter(0x7ce)
            self.dongle.setCanID(0x7c6)
            raw[b22b002] = self.dongle.sendCommand(b22b002)
            if len(raw[b22b002][0x7ce]) == 3:
                data['EXTENDED'].update({
                    'odo':                  ffbu(raw[b22b002][0x7ce][1][3:6]),
                    })

        data['ADDITIONAL'] = {
                'cumulativeChargeCurrent':  ifbu(raw[b2101][0x7ec][4][5:7] + raw[b2101][0x7ec][5][0:2]) / 10.0,
                'cumulativeDischargeCurrent': ifbu(raw[b2101][0x7ec][5][2:6]) / 10.0,

                'batteryAvgTemperature':    sum(cellTemps) / len(cellTemps),
                'driveMotorSpeed':          ifbs(raw[b2101][0x7ec][8][0:2]),

                'fanStatus':                ifbu(raw[b2101][0x7ec][4][2:3]),
                'fanFeedback':              ifbu(raw[b2101][0x7ec][4][3:4]),

                'availableChargePower':     ifbu(raw[b2101][0x7ec][1][1:3]) / 100.0,
                'availableDischargePower':  ifbu(raw[b2101][0x7ec][1][3:5]) / 100.0,

                'obdVoltage':               self.dongle.getObdVoltage(),
                }

        for i,temp in enumerate(cellTemps):
            key = "cellTemp{:02d}".format(i+1)
            data['ADDITIONAL'][key] = float(temp)

        for i,cvolt in enumerate(cellVoltages):
            key = "cellVoltage{:02d}".format(i+1)
            data['ADDITIONAL'][key] = float(cvolt)

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def getABRPModel(self): return 'hyundai:ioniq:17:28:other'

    def getEVNModel(self): return 'IONIQ_BEV'

