from car import *

class KONA_EV(Car):

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter('7EC')
        self.dongle.setCANRxMask('7FF')

    def getData(self):
        raw = {}

        volt = self.dongle.getObdVoltage()
        if volt and volt < 13.0:
            raise KONA_EV.LOW_VOLTAGE(volt)

        for cmd in [220101,220105]:
            raw[cmd] = self.dongle.sendCommand(str(cmd))

        data = self.getBaseData()

        data['SOC_BMS'] = raw[220101][0x7EC][1][2] / 2.0
        data['SOC_DISPLAY'] = raw[220105][0x7EC][5][0] / 2.0

        chargingBits = raw[220101][0x7EC][1][5]
        normalChargePort = raw[220101][0x7EC][1][6] == 3
        normalChargeBit = chargingBits & 0x02 == 0x02
        dcBatteryCurrent = int.from_bytes(raw[220101][0x7EC][2][0:2], byteorder='big', signed=True) / 10.0
        dcBatteryVoltage = int.from_bytes(raw[220101][0x7EC][2][2:4], byteorder='big', signed=False) / 10.0

        data['EXTENDED'] = {
                'auxBatteryVoltage':        raw[220101][0x7EC][4][5] / 10.0,
                'batteryInletTemperature':  int.from_bytes(raw[220101][0x7EC][3][5:6], byteorder='big', signed=True),
                'batteryMaxTemperature':    int.from_bytes(raw[220101][0x7EC][2][4:5], byteorder='big', signed=True),
                'batteryMinTemperature':    int.from_bytes(raw[220101][0x7EC][2][5:6], byteorder='big', signed=True),
                'charging':                 1 if chargingBits & 0x10 else 0,
                'normalChargePort':         1 if normalChargeBit and normalChargePort else 0,
                'rapidChargePort':          1 if normalChargeBit and not normalChargePort else 0,
                'dcBatteryCurrent':         dcBatteryCurrent,
                'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
                'dcBatteryVoltage':         dcBatteryVoltage,
                'soh':                      int.from_bytes(raw[220105][0x7EC][4][1:3], byteorder='big', signed=False) / 10.0,
                }

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }
