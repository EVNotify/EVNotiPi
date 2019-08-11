from car import *
from time import time

b2101 = bytes.fromhex(hex(0x2101)[2:])
b2105 = bytes.fromhex(hex(0x2105)[2:])
b2180 = bytes.fromhex(hex(0x2180)[2:])

class IONIQ_BEV(Car):

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCANRxMask(0x7ff)

    def getData(self):
        now = time()
        raw = {}

        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCanID(0x7e4)
        for cmd in [b2101,b2105]:
            raw[cmd] = self.dongle.sendCommand(cmd)

        self.dongle.setCANRxFilter(0x7ee)
        self.dongle.setCanID(0x7e6)
        raw[b2180] = self.dongle.sendCommand(b2180)

        if len(raw[b2101][0x7ec]) != 9 or \
                len(raw[b2105][0x7ec]) != 7 or \
                len(raw[b2180][0x7ee]) != 4:
            raise IONIQ_BEV.NULL_BLOCK("Got wrong count of frames!\n"+str(raw))

        if raw[b2101][0x7ec][7] == b'\x00\x00\x00\x00\x00\x00\x00':
            raise IONIQ_BEV.NULL_BLOCK("Got Null Block!\n"+str(raw))

        data = self.getBaseData()

        data['SOC_BMS']     = raw[b2101][0x7ec][1][0] / 2.0
        data['SOC_DISPLAY'] = raw[b2105][0x7ec][4][6] / 2.0

        chargingBits = raw[b2101][0x7ec][1][5]
        dcBatteryCurrent = int.from_bytes(raw[b2101][0x7ec][1][6:7] + raw[b2101][0x7ec][2][0:1], byteorder='big', signed=True) / 10.0
        dcBatteryVoltage = int.from_bytes(raw[b2101][0x7ec][2][1:3], byteorder='big', signed=False) / 10.0

        # Calc avg battery temp
        avgBattTemp = (
                int.from_bytes(raw[b2101][0x7ec][2][5:6], byteorder='big', signed=True) +
                int.from_bytes(raw[b2101][0x7ec][2][6:7], byteorder='big', signed=True) +

                int.from_bytes(raw[b2101][0x7ec][3][0:1], byteorder='big', signed=True) +
                int.from_bytes(raw[b2101][0x7ec][3][1:2], byteorder='big', signed=True) +
                int.from_bytes(raw[b2101][0x7ec][3][2:3], byteorder='big', signed=True) +

                int.from_bytes(raw[b2105][0x7ec][1][5:6], byteorder='big', signed=True) +
                int.from_bytes(raw[b2105][0x7ec][1][6:7], byteorder='big', signed=True) +

                int.from_bytes(raw[b2105][0x7ec][2][0:1], byteorder='big', signed=True) +
                int.from_bytes(raw[b2105][0x7ec][2][1:2], byteorder='big', signed=True) +
                int.from_bytes(raw[b2105][0x7ec][2][2:3], byteorder='big', signed=True) +
                int.from_bytes(raw[b2105][0x7ec][2][3:4], byteorder='big', signed=True) +
                int.from_bytes(raw[b2105][0x7ec][2][4:5], byteorder='big', signed=True) ) / 12

        data['EXTENDED'] = {
                'auxBatteryVoltage':        raw[b2101][0x7ec][4][4] / 10.0,
                'batteryInletTemperature':  int.from_bytes(raw[b2101][0x7ec][3][2:3], byteorder='big', signed=True),
                'batteryMaxTemperature':    int.from_bytes(raw[b2101][0x7ec][2][3:4], byteorder='big', signed=True),
                'batteryMinTemperature':    int.from_bytes(raw[b2101][0x7ec][2][4:5], byteorder='big', signed=True),
                'batteryAvgTemperature':    avgBattTemp,
                'charging':                 1 if chargingBits & 0x80 else 0,
                'normalChargePort':         1 if chargingBits & 0x20 else 0,
                'rapidChargePort':          1 if chargingBits & 0x40 else 0,
                'dcBatteryCurrent':         dcBatteryCurrent,
                'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
                'dcBatteryVoltage':         dcBatteryVoltage,
                'soh':                      int.from_bytes(raw[b2105][0x7ec][4][0:2], byteorder='big', signed=False) / 10.0,
                'cumulativeEnergyCharged':  int.from_bytes(raw[b2101][0x7ec][5][6:7] + raw[b2101][0x7ec][6][0:3], byteorder='big', signed=False) / 10.0,
                'cumulativeEnergyDischarged': int.from_bytes(raw[b2101][0x7ec][6][3:7], byteorder='big', signed=False) / 10.0,
                'externalTemperature':      (raw[b2180][0x7ee][2][1] - 80) / 2,
                }

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }

