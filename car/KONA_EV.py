from .car import Car
from time import time

b220100 = bytes.fromhex('220100')
b220101 = bytes.fromhex('220101')
b220105 = bytes.fromhex('220105')
b22b002 = bytes.fromhex('22b002')

class KONA_EV(Car):

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self.dongle.setProtocol('CAN_11_500')

    def readDongle(self, data):
        now = time()
        raw = {}

        for cmd in [b220101,b220105]:
            raw[cmd] = self.dongle.sendCommandEx(cmd, canrx=0x7ec, cantx=0x7e4)

        try:
            raw[b22b002] = self.dongle.sendCommandEx(b22b002, canrx=0x7ce, cantx=0x7c6)
        except NoData:
            # 0x7ce is only available while driving
            pass

        data.update(self.getBaseData())

        chargingBits = raw[b220101][53]
        dcBatteryCurrent = ifbs(raw[b220101][13:15]) / 10.0
        dcBatteryVoltage = ifbu(raw[b220101][15:17]) / 10.0

        data.update({
            # Base:
            'SOC_BMS':                  raw[b220101][7] / 2.0,
            'SOC_DISPLAY':              raw[b220105][34] / 2.0,
            # Extended:
            'auxBatteryVoltage':        raw[b220101][32] / 10.0,
            'batteryInletTemperature':  ifbs(raw[b220101][25:26]),
            'batteryMaxTemperature':    ifbs(raw[b220101][17:18]),
            'batteryMinTemperature':    ifbs(raw[b220101][18:19]),
            'cumulativeEnergyCharged':  ifbu(raw[b220101][41:45]) / 10.0,
            'cumulativeEnergyDischarged': ifbu(raw[b220101][45:49]) / 10.0,
            'charging':                 1 if (chargingBits & 0xc) == 0x8 else 0,
            'normalChargePort':         1 if (chargingBits & 0x80) and raw[b220101][12] == 3 else 0,
            'rapidChargePort':          1 if (chargingBits & 0x80) and raw[b220101][12] != 3 else 0,
            'dcBatteryCurrent':         dcBatteryCurrent,
            'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
            'dcBatteryVoltage':         dcBatteryVoltage,
            'soh':                      ifbu(raw[b220105][28:30]) / 10.0,
            #'externalTemperature':      (raw[b220100][0x7ce][1][3] - 80) / 2.0,
            'odo':                      ffbu(raw[b22b002][11:15]) if b22b002 in raw else None,
            })

    def getBaseData(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }
