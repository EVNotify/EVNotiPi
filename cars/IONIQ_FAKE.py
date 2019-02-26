
class IONIQ_FAKE:

    def __init__(self, dongle):
        pass

    def getData(self):
        raw = {}

        lines = {
                2101: [
                    b'7EC103D6101FFFFFFFF',
                    b'7EC217626482648A3FF',
                    b'7EC22970E3609080909',
                    b'7EC230808090007BD0D',
                    b'7EC24BD0A0000800001',
                    b'7EC25E4D90001E44A00',
                    b'7EC2600B2130000AC45',
                    b'7EC270054BFE909016B',
                    b'7EC280000000003E800'],
                2105: [
                    b'7EC102D6105FFFFFFFF',
                    b'7EC2100000000000808',
                    b'7EC2209080808082648',
                    b'7EC2326480001500707',
                    b'7EC2403E81203E82B7A',
                    b'7EC2500310000000000',
                    b'7EC2600000000000000']
                }

        for cmd in [2101,2105]:
            raw[cmd] = {}
            for line in lines[cmd]: #self.dongle.sendCommand(str(cmd)):
                raw[cmd][int(line[:5],16)] = bytes.fromhex(str(line[5:],'ascii'))

        chargingBits = raw[2101][0x7EC21][5] \
                if 0x7EC21 in raw[2101] else None
        dcBatteryCurrent = int.from_bytes(raw[2101][0x7EC21][6:7] + raw[2101][0x7EC22][0:1], byteorder='big', signed=True) / 10.0 \
                if 0x7EC21 in raw[2101] and 0x7EC22 in raw[2101] else None
        dcBatteryVoltage = int.from_bytes(raw[2101][0x7EC22][1:3], byteorder='big', signed=False) / 10.0 \
                if 0x7EC22 in raw[2101] else None

        data = {'SOC_BMS':      raw[2101][0x7EC21][0] / 2.0 \
                    if 0x7EC21 in raw[2101] else None,
                'SOC_DISPLAY':  raw[2105][0x7EC24][6] / 2.0 \
                    if 0x7EC24 in raw[2105] else None,
                'EXTENDED': {
                    'auxBatteryVoltage':        raw[2101][0x7EC24][4] / 10.0 \
                        if 0x7EC24 in raw[2105] else None,
                    'batteryInletTemperature':  int.from_bytes(raw[2101][0x7EC23][2:3], byteorder='big', signed=True) \
                        if 0x7EC23 in raw[2105] else None,
                    'batteryMaxTemperature':    int.from_bytes(raw[2101][0x7EC22][3:4], byteorder='big', signed=True) \
                        if 0x7EC22 in raw[2105] else None,
                    'batteryMinTemperature':    int.from_bytes(raw[2101][0x7EC22][4:5], byteorder='big', signed=True) \
                        if 0x7EC22 in raw[2105] else None,
                    'charging':                 1 if chargingBits != None and \
                            chargingBits & 0x80 == 0x80 else 0,
                    'normalChargePort':         1 if chargingBits != None and \
                            chargingBits & 0x20 == 0x20 else 0,
                    'rapidChargePort':          1 if chargingBits != None and \
                            chargingBits & 0x40 == 0x40 else 0,
                    'dcBatteryCurrent':         dcBatteryCurrent,
                    'dcBatteryPower':           dcBatteryCurrent * dcBatteryVoltage / 1000.0 \
                        if dcBatteryCurrent!= None and dcBatteryVoltage != None else None,
                    'dcBatteryVoltage':         dcBatteryVoltage,
                    'soh':                      int.from_bytes(raw[2105][0x7EC24][0:2], byteorder='big', signed=False) / 10.0 \
                        if 0x7EC24 in raw[2105] else None,
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


if __name__ == '__main__':
    car = IONIQ_FAKE(None)
    print(car.getData())

