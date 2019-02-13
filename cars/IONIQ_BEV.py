
def signedHex(txt):
    bits = len(txt) * 4
    return (int(txt, 16) + 2**(bits-1)) % 2**bits - 2**(bits-1)


class IONIQ_BEV:

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter('7EC')
        self.dongle.setCANRxMask('7FF')

    def getData(self):
        raw = {}

        # Collect both parts of DC Current
        dcCurrent = [None,None]
        data = {'EXTENDED': {}}

        for line in self.dongle.sendCommand('2101'):
            can_id = line[:5]
            can_data = line[5:]

            if can_id == b'7EC21':
                chargingBits = int(can_data[-4:-2],16)
                dcCurrent[0] = can_data[12:14]
                data.update({
                    'SOC_BMS':          int(can_data[0:2],16) / 2.0,
                    })
                data['EXTENDED'].update({
                    'charging':         1 if chargingBits & 0x80 == 0x80 else 0,
                    'rapidChargePort':  1 if chargingBits & 0x40 == 0x40 else 0,
                    'normalChargePort': 1 if chargingBits & 0x20 == 0x20 else 0,
                    })

            elif can_id == b'7EC22':
                dcCurrent[1] = can_data[0:2]
                data['EXTENDED'].update({
                    'dcBatteryVoltage':        int(can_data[2:6],16) / 10.0,
                    'batteryMinTemperature':   signedHex(can_data[8:10]),
                    'batteryMaxTemperature':   signedHex(can_data[6:8]),
                    })

            elif can_id == b'7EC23':
                data['EXTENDED'].update({
                    'batteryInletTemperature': signedHex(can_data[4:6]),
                    })

            elif can_id == b'7EC24':
                data['EXTENDED'].update({
                    'auxBatteryVoltage': int(can_data[8:10],16) / 10.0,
                    })


        data['EXTENDED']['dcBatteryCurrent'] = \
                signedHex(b''.join(dcCurrent)) / 10.0


        for line in self.dongle.sendCommand('2105'):
            can_id = line[:5]
            can_data = line[5:]

            if can_id == b'7EC24':
                data.update({
                    'SOC_DISPLAY': int(can_data[-2:],16) / 2.0,
                    })
                data['EXTENDED'].update({
                    'soh': int(can_data[0:4],16) / 10.0,
                    })


        data['EXTENDED']['dcBatteryPower'] = \
                data['EXTENDED']['dcBatteryVoltage'] * \
                data['EXTENDED']['dcBatteryCurrent'] / 1000.0

        data.update(self.getBaseData())

        return data

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }
