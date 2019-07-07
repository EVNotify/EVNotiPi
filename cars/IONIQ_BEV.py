from car import *
from time import time

POLL_DELAY_2180 = 60    # Rate limit b2180 to once a minute
b2101 = bytes.fromhex(hex(0x2102)[2:])
b2105 = bytes.fromhex(hex(b2105)[2:])
b2180 = bytes.fromhex(hex(b2180)[2:])

class IONIQ_BEV(Car):

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter(0x7ec)
        self.dongle.setCANRxMask(0x7ff)
        self.car_on_voltage = None
        self.last_raw = {}
        self.last_poll_2180 = 0

    def getData(self):
        now = time()
        raw = {}

        volt = self.dongle.getObdVoltage() * 0.69
        if self.car_on_voltage and volt and volt < (self.car_on_voltage * 0.94):
            #print("Skip poll, Voltage indicates car off {}/{}".format(volt, self.car_on_voltage * 0.91))
            raise IONIQ_BEV.LOW_VOLTAGE(volt)

        self.dongle.setCANRxFilter(0x7ec)
        for cmd in [b2101,b2105]:
            raw[cmd] = self.dongle.sendCommand(cmd)

        if now - self.last_poll_2180 > POLL_DELAY_2180 or b2180 not in self.last_raw:
            self.last_poll_2180 = now
            self.dongle.setCANRxFilter(0x7ee)
            raw[b2180] = self.dongle.sendCommand(b2180)
        else:
            raw[b2180] = self.last_raw[b2180]

        if len(raw[b2101][0x7ec]) != 9 or \
                len(raw[b2105][0x7ec]) != 7 or \
                len(raw[b2180][0x7ee]) != 4:
            raise IONIQ_BEV.NULL_BLOCK("Got wrong count of frames!\n"+str(raw))


        if raw[b2101][0x7ec][7] == b'\x00\x00\x00\x00\x00\x00\x00':
            raise IONIQ_BEV.NULL_BLOCK("Got Null Block!\n"+str(raw))

        self.last_raw[b2180] = raw[b2180]

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
                'driveMotorSpeed':          int.from_bytes(raw[b2101][0x7ec][8][0:2], byteorder='big', signed=True),
                'outsideTemp':              (raw[b2180][0x7ee][2][1] - 80) / 2,
                'auxBatteryVoltage2':       volt,
                }

        if data['EXTENDED']['auxBatteryVoltage'] > 13.0:
            self.car_on_voltage = volt


        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }

