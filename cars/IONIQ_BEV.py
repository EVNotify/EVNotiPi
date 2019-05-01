from car import *

class IONIQ_BEV(Car):

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter('7EC')
        self.dongle.setCANRxMask('7FF')
        self.car_on_voltage = None

    def getData(self):
        raw = {}

        volt = self.dongle.getObdVoltage()
        if self.car_on_voltage and volt and volt < (self.car_on_voltage * 0.95):
            print("Skip poll, Voltage indicates car off {}/{} => {}".format(volt, self.car_on_voltage*0.95, volt * 0.7))
            raise IONIQ_BEV.LOW_VOLTAGE(volt)

        for cmd in [2101,2105]:
            raw[cmd] = self.dongle.sendCommand(str(cmd))

        if 0x7EC27 in raw[2101] and raw[2101][0x7EC27] == b'\x00\x00\x00\x00\x00\x00\x00':
            raise IONIQ_BEV.NULL_BLOCK("Got Null Block!\n"+str(raw))

        data = self.getBaseData()

        if 0x7EC21 in raw[2101]:
            data['SOC_BMS']     = raw[2101][0x7EC21][0] / 2.0
        if 0x7EC24 in raw[2105]:
            data['SOC_DISPLAY'] = raw[2105][0x7EC24][6] / 2.0

        if set([0x7EC21,0x7EC22,0x7EC23,0x7EC24]).issubset(raw[2101]) and \
                set([0x7EC23,0x7EC24]).issubset(raw[2105]):

            chargingBits = raw[2101][0x7EC21][5]
            dcBatteryCurrent = int.from_bytes(raw[2101][0x7EC21][6:7] + raw[2101][0x7EC22][0:1], byteorder='big', signed=True) / 10.0
            dcBatteryVoltage = int.from_bytes(raw[2101][0x7EC22][1:3], byteorder='big', signed=False) / 10.0

            data['EXTENDED'] = {
                    'auxBatteryVoltage':        raw[2101][0x7EC24][4] / 10.0,
                    'batteryInletTemperature':  int.from_bytes(raw[2101][0x7EC23][2:3], byteorder='big', signed=True),
                    'batteryMaxTemperature':    int.from_bytes(raw[2101][0x7EC22][3:4], byteorder='big', signed=True),
                    'batteryMinTemperature':    int.from_bytes(raw[2101][0x7EC22][4:5], byteorder='big', signed=True),
                    'charging':                 1 if chargingBits & 0x80 else 0,
                    'normalChargePort':         1 if chargingBits & 0x20 else 0,
                    'rapidChargePort':          1 if chargingBits & 0x40 else 0,
                    'dcBatteryCurrent':         dcBatteryCurrent,
                    'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0,
                    'dcBatteryVoltage':         dcBatteryVoltage,
                    'soh':                      int.from_bytes(raw[2105][0x7EC24][0:2], byteorder='big', signed=False) / 10.0,
                    'cumChargeEnergy':          int.from_bytes(raw[2101][0x7EC25][6:7] + raw[2101][0x7EC26][0:3], byteorder='big', signed=False),
                    'cumDischargeEnergy':       int.from_bytes(raw[2101][0x7EC26][3:7], byteorder='big', signed=False),
                    'driveMotorSpeed':          int.from_bytes(raw[2101][0x7EC28][0:2], byteorder='big', signed=True),
                }

            if data['EXTENDED']['auxBatteryVoltage'] > 13.0:
                if not self.car_on_voltage or self.car_on_voltage < volt:
                    self.car_on_voltage = volt


        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }

