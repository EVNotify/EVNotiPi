from car import *

b220100 = bytes.fromhex('220100')
b220101 = bytes.fromhex('220101')
b220105 = bytes.fromhex('220105')
b22b002 = bytes.fromhex('22b002')

class KONA_EV(Car):

    def __init__(self, config, dongle):
        Car.__init__(self, config, dongle)
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxMask(0x7ff)

    def readDongle(self):
        now = time()
        raw = {}

        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCanID(0x7e4)
        for cmd in [b220101,b220105]:
            raw[cmd] = self.dongle.sendCommand(cmd)

        self.dongle.setCANRxFilter(0x7ce)
        self.dongle.setCanID(0x7c6)
        raw[b220100] = self.dongle.sendCommand(b220100)
        raw[b22b002] = self.dongle.sendCommand(b22b002)

        data = self.getBaseData()

        data['timestamp'] = now
        data['SOC_BMS'] = raw[b220101][0x7ec][1][2] / 2.0
        data['SOC_DISPLAY'] = raw[b220105][0x7ec][5][0] / 2.0

        chargingBits = raw[b220101][0x7ec][1][6]
        dcBatteryCurrent = ifbs(raw[b220101][0x7ec][2][0:2]) / 10.0
        dcBatteryVoltage = ifbu(raw[b220101][0x7ec][2][2:4]) / 10.0

        data['EXTENDED'] = {
                'auxBatteryVoltage':        raw[b220101][0x7ec][4][5] / 10.0,
                'batteryInletTemperature':  ifbs(raw[b220101][0x7ec][3][5:6]),
                'batteryMaxTemperature':    ifbs(raw[b220101][0x7ec][2][4:5]),
                'batteryMinTemperature':    ifbs(raw[b220101][0x7ec][2][5:6]),
                'charging':                 1 if chargingBits & 0x40 else 0,
                'normalChargePort':         1 if chargingBits & 0x10 else 0,
                'rapidChargePort':          1 if chargingBits & 0x20 else 0,
                'dcBatteryCurrent':         dcBatteryCurrent,
                'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
                'dcBatteryVoltage':         dcBatteryVoltage,
                'soh':                      ifbu(raw[b220105][0x7ec][4][1:3]) / 10.0,
                'externalTemperature':      (raw[b220100][0x7ee][1][3] - 80) / 2.0,
                'odo':                      ffbu(raw[b22b002][0x7ce][1][5:7] + raw[b22b002][0x7ce][2][0:2]),
                }

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }
