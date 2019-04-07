
class KONA_EV:

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter('7EC')
        self.dongle.setCANRxMask('7FF')

    def getData(self):
        raw = {}

        for cmd in [220101,220105]:
            raw[cmd] = self.dongle.sendCommand(str(cmd))

        dchargingBits = raw[220101][0x7EC21][5] \
                if 0x7EC21 in raw[220101] else None

        normalChargePort = raw[220101][0x7EC21][6] == 3 \
                if 0x7EC21 in raw[220101] else None
        normalChargeBit = chargingBits & 0x02 == 0x02

        dcBatteryCurrent = int.from_bytes(raw[220101][0x7EC22][0:2], byteorder='big', signed=True) / 10.0 \
                if 0x7EC22 in raw[220101] else None

        dcBatteryVoltage = int.from_bytes(raw[220101][0x7EC22][2:4], byteorder='big', signed=False) / 10.0 \
                if 0x7EC22 in raw[220101] else None

        data = {'SOC_BMS':      raw[220101][0x7EC21][2] / 2.0 \
                    if 0x7EC21 in raw[220101] else None,
                'SOC_DISPLAY':  raw[220105][0x7EC25][0] / 2.0 \
                    if 0x7EC25 in raw[220105] else None,
                'EXTENDED': {
                    'auxBatteryVoltage':        raw[220101][0x7EC24][5] / 10.0 \
                        if 0x7EC24 in raw[220101] else None,
                    'batteryInletTemperature':  int.from_bytes(raw[220101][0x7EC23][5:6], byteorder='big', signed=True) \
                        if 0x7EC23 in raw[220101] else None,
                    'batteryMaxTemperature':    int.from_bytes(raw[220101][0x7EC22][4:5], byteorder='big', signed=True) \
                        if 0x7EC22 in raw[220101] else None,
                    'batteryMinTemperature':    int.from_bytes(raw[220101][0x7EC22][5:6], byteorder='big', signed=True) \
                        if 0x7EC22 in raw[220101] else None,
                    'charging':                 1 if chargingBits != None and \
                            chargingBits & 0x10 == 0x10 else 0,
                    'normalChargePort':         1 if normalChargeBit and normalChargePort else 0,
                    'rapidChargePort':          1 if normalChargeBit and not normalChargePort else 0,
                    'dcBatteryCurrent':         dcBatteryCurrent,
                    'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0 \
                        if dcBatteryCurrent!= None and dcBatteryVoltage != None else None,
                    'dcBatteryVoltage':         dcBatteryVoltage,
                    'soh':                      int.from_bytes(raw[220105][0x7EC24][1:3], byteorder='big', signed=False) / 10.0 \
                        if 0x7EC24 in raw[220105] else None,
                    }
                }

        data.update(self.getBaseData())

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }
