
def signedHex(txt):
    bits = len(txt) * 4
    return (int(txt, 16) + 2**(bits-1)) % 2**bits - 2**(bits-1)


class KONA_EV:

    def __init__(self, dongle):
        self.dongle = dongle
        self.dongle.setProtocol('CAN_11_500')
        self.dongle.setCANRxFilter('7EC')
        self.dongle.setCANRxMask('7FF')

    def getData(self):
        raw = {}

        normalChargePort = None
        normalChargeBit = None
        data = {'EXTENDED': {}}


        for line in self.dongle.sendCommand('220101'):
            can_id = line[:5]
            can_data = line[5:]

            if can_id == b'7EC21':
                normalChargePort = can_data[12:14] == '03'
                data.update({
                    'SOC_BMS':          int(can_data[2:4],16) / 2.0,
                    })

            elif can_id == b'7EC22':
                chargingBits = int(can_data[2:4],16)
                normalChargeBit = chargingBits & 0x02 == 0x02
                data['EXTENDED'].update({
                    'charging':                1 if chargingBits & 0x01 == 0x01 else 0,
                    'batteryMinTemperature':   signedHex(can_data[10:12]),
                    'batteryMaxTemperature':   signedHex(can_data[8:10]),
                    'dcBatteryCurrent':        signedHex(can_data[0:4]) / 10.0,
                    'dcBatteryVoltage':        int(can_data[4:8],16) / 10.0,
                    })

            elif can_id == b'7EC23':
                data['EXTENDED'].update({
                    'batteryInletTemperature': signedHex(can_data[10:12]),
                    })

            elif can_id == b'7EC24':
                data['EXTENDED'].update({
                    'auxBatteryVoltage': int(can_data[10:12],16) / 10.0,
                    })


        data['EXTENDED'].update({
            'normalChargePort': 1 if normalChargeBit and normalChargePort else 0,
            'rapidChargePort':  1 if normalChargeBit and not normalChargePort else 0,
            })

        for line in self.dongle.sendCommand('220105'):
            can_id = line[:5]
            can_data = line[5:]

            if can_id == b'7EC25':
                data.update({
                    'SOC_DISPLAY': int(can_data[0:2],16) / 2.0,
                    })
            elif can_id == b'7EC24':
                data['EXTENDED'].update({
                    'soh': int(can_data[2:6],16) / 10.0,
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
