""" Module for the Hyundai Kona EV """
from .car import Car
from .isotp_decoder import IsoTpDecoder

b220100 = bytes.fromhex('220100')
b220101 = bytes.fromhex('220101')
b220102 = bytes.fromhex('220102')
b220103 = bytes.fromhex('220103')
b220104 = bytes.fromhex('220104')
b220105 = bytes.fromhex('220105')
b22b002 = bytes.fromhex('22b002')

Fields = (
    {'cmd': b220101, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'SOC_BMS', 'width': 1, 'scale': .5},
         {'padding': 4},
         {'name': 'charging_bits1', 'width': 1},
         {'name': 'dcBatteryCurrent', 'width': 2, 'signed': True, 'scale': .1},
         {'name': 'dcBatteryVoltage', 'width': 2, 'scale': .1},
         {'name': 'batteryMaxTemperature', 'width': 1, 'signed': True},
         {'name': 'batteryMinTemperature', 'width': 1, 'signed': True},
         {'name': 'cellTemp%02d', 'idx': 1, 'cnt': 4, 'width': 1, 'signed': True},
         {'padding': 2},
         {'name': 'batteryInletTemperature', 'width': 1, 'signed': True},
         {'padding': 6},
         {'name': 'auxBatteryVoltage', 'width': 1, 'scale': .1},
         {'name': 'cumulativeChargeCurrent', 'width': 4, 'scale': .1},
         {'name': 'cumulativeDischargeCurrent', 'width': 4, 'scale': .1},
         {'name': 'cumulativeEnergyCharged', 'width': 4, 'scale': .1},
         {'name': 'cumulativeEnergyDischarged', 'width': 4, 'scale': .1},
         {'name': 'operatingTime', 'width': 4},  # seconds
         {'name': 'charging_bits2', 'width': 1},
         {'padding': 8},
     )
     },
    {'cmd': b220102, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'cellVoltage%02d', 'idx': 1, 'cnt': 32, 'width': 1, 'scale': .02},
     )
     },
    {'cmd': b220103, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'cellVoltage%02d', 'idx': 33, 'cnt': 32, 'width': 1, 'scale': .02},
     )
     },
    {'cmd': b220104, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 7},
         {'name': 'cellVoltage%02d', 'idx': 65, 'cnt': 32, 'width': 1, 'scale': .02},
     )
     },
    {'cmd': b220105, 'canrx': 0x7ec, 'cantx': 0x7e4,
     'fields': (
         {'padding': 28},
         {'name': 'soh', 'width': 2, 'scale': .1},
         {'padding': 4},
         {'name': 'SOC_DISPLAY', 'width': 1, 'scale': .5},
         {'padding': 11},
     )
     },
    {'cmd': b220100, 'canrx': 0x7bb, 'cantx': 0x7b3,
     'fields': (
         {'padding': 8},
         {'name': 'internalTemperature', 'width': 1, 'scale': .5, 'offset': -40},
         {'name': 'externalTemperature', 'width': 1, 'scale': .5, 'offset': -40},
         {'padding': 28},
     )
     },
    {'cmd': b22b002, 'canrx': 0x7ce, 'cantx': 0x7c6, 'optional': True,
     'fields': (
         {'padding': 9},
         {'name': 'odo', 'width': 3},
         {'padding': 3},
     )
     },
    {'computed': True,
     'fields': (
         {'name': 'dcBatteryPower',
          'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
         {'name': 'charging',
          'lambda': lambda d: int(d['charging_bits2'] & 0xc == 0x8)},
         {'name': 'normalChargePort',
          'lambda': lambda d: int((d['charging_bits2'] & 0x80) != 0 and d['charging_bits1'] == 3)},
         {'name': 'rapidChargePort',
          'lambda': lambda d: int((d['charging_bits2'] & 0x80) != 0 and d['charging_bits1'] != 3)},
     )
     },
)


class KonaEv(Car):
    """ Decoder class for Hyundai Kona EV """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self._dongle, Fields)

    def read_dongle(self, data):
        """ Read and parse data from dongle """
        data.update(self.get_base_data())
        data.update(self._isotp.get_data())

    def get_base_data(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def get_evn_model(self):
        return 'KONA_EV'
