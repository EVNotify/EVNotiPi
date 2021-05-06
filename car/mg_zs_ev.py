""" Module for the MG ZS EV """
from .car import Car
from .isotp_decoder import IsoTpDecoder

BMS_RX = 0x789
BMS_TX = 0x781
DCDC_RX = 0x785
DCDC_TX = 0x78d
VCU_RX = 0x7eb
VCU_TX = 0x7e3
ATC_RX = 0x758
ATC_TX = 0x750
BCM_RX = 0x748
BCM_TX = 0x740
TPMS_RX = 0x72c
TPMS_TX = 0x724
IPK_RX = 0x768
IPK_TX = 0x760

CMD_AUX_VOLTAGE = bytes.fromhex('220112')   # VCU
CMD_CHARGE_STATE = bytes.fromhex('22b71b')  # VCU (1=connected, 0=disconnected)
CMD_SOC_BMS = bytes.fromhex('22b046')       # BMS
#CMD_SOC = bytes.fromhex('229001')
CMD_VOLTAGE = bytes.fromhex('22b042')       # BMS
CMD_CURRENT = bytes.fromhex('22b043')       # BMS
CMD_ODO = bytes.fromhex('22b101')           # IPK
CMD_SOH = bytes.fromhex('22b061')           # BMS
CMD_IGNITION = bytes.fromhex('22b18c')      # VCU
CMD_OUT_TEMP = bytes.fromhex('22e01b')      # ATC

Fields = [
    {'cmd': CMD_AUX_VOLTAGE, 'canrx': VCU_RX, 'cantx': VCU_TX,
     'fields': (
         {'padding': 3},
         {'name': 'auxBatteryVoltage', 'width': 1, 'scale': .1},
     )
     },
    {'cmd': CMD_CHARGE_STATE, 'canrx': VCU_RX, 'cantx': VCU_TX,
     'fields': (
         {'padding': 3},
         {'name': 'charge_state', 'width': 1},
     )
     },
    # {'cmd': CMD_SOC, 'canrx': BMS_RX, 'cantx': BMS_TX,
    #  'fields': (
    #      {'padding': 3},
    #      {'name': 'SOC_DISPLAY', 'width': 2, 'scale': .01},
    #  )
    #  },
    {'cmd': CMD_SOC_BMS, 'canrx': BMS_RX, 'cantx': BMS_TX,
     'fields': (
         {'padding': 3},
         {'name': 'SOC_BMS', 'width': 2, 'scale': .1},
     )
     },
    {'cmd': CMD_VOLTAGE, 'canrx': BMS_RX, 'cantx': BMS_TX,
     'fields': (
         {'padding': 3},
         {'name': 'dcBatteryVoltage', 'width': 2, 'scale': .25},
     )
     },
    {'cmd': CMD_CURRENT, 'canrx': BMS_RX, 'cantx': BMS_TX,
     'fields': (
         {'padding': 3},
         {'name': 'dcBatteryCurrent', 'width': 2, 'offset': -1000, 'scale': .025},
     )
     },
    {'cmd': CMD_ODO, 'canrx': IPK_RX, 'cantx': IPK_TX,
     'fields': (
         {'padding': 3},
         {'name': 'odo', 'width': 3},
     )
     },
    {'cmd': CMD_SOH, 'canrx': BMS_RX, 'cantx': BMS_TX,
     'fields': (
         {'padding': 3},
         {'name': 'soh', 'width': 2, 'scale': .01},
     )
     },
    {'cmd': CMD_OUT_TEMP, 'canrx': ATC_RX, 'cantx': ATC_TX,
     'fields': (
         {'padding': 3},
         {'name': 'externalTemperature', 'width': 2, 'scale': .1, 'offset': -40},
     )
     },
    {'computed': True,
     'fields': (
         {'name': 'dcBatteryPower',
          'lambda': lambda d: d['dcBatteryCurrent'] * d['dcBatteryVoltage'] / 1000.0},
         {'name': 'charging',
          'lambda': lambda d: int(d['charge_state'] != 0)},
     )
     },
]


class MgZsEv(Car):
    """ Class for MG ZS EV """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._isotp = IsoTpDecoder(self._dongle, Fields)

    def read_dongle(self, data):
        """ Read and parse data from dongle """
        data.update(self.get_base_data())
        data.update(self._isotp.get_data())

    @staticmethod
    def get_base_data():
        return {
            "CAPACITY": 42,
            "SLOW_SPEED": 3.6,
            "NORMAL_SPEED": 6.6,
            "FAST_SPEED": 76.0
        }

    @staticmethod
    def get_abrp_model():
        return ''

    @staticmethod
    def get_evn_model():
        return 'MG_ZS_EV'
