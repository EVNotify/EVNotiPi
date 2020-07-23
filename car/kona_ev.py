""" Module for the Hyundai Kona EV """
from .car import Car, ifbs, ifbu, ffbu
from ..dongle import NoData

b220100 = bytes.fromhex('220100')
b220101 = bytes.fromhex('220101')
b220105 = bytes.fromhex('220105')
b22b002 = bytes.fromhex('22b002')


class KonaEv(Car):
    """ Class for Hyundai Kona EV """

    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')

    def read_dongle(self, data):
        """ Read and parse data from dongle """
        raw = {}

        for cmd in [b220101, b220105]:
            raw[cmd] = self._dongle.send_command_ex(cmd, canrx=0x7ec, cantx=0x7e4)

        try:
            raw[b22b002] = self._dongle.send_command_ex(b22b002, canrx=0x7ce, cantx=0x7c6)
        except NoData:
            # 0x7ce is only available while driving
            pass

        data.update(self.get_base_data())

        charging_bits = raw[b220101][53]
        dc_battery_current = ifbs(raw[b220101][13:15]) / 10.0
        dc_battery_voltage = ifbu(raw[b220101][15:17]) / 10.0

        data.update({
            # Base:
            'SOC_BMS':                  raw[b220101][7] / 2.0,
            'SOC_DISPLAY':              raw[b220105][34] / 2.0,
            # Extended:
            'auxBatteryVoltage':        raw[b220101][32] / 10.0,
            'batteryInletTemperature':  ifbs(raw[b220101][25:26]),
            'batteryMaxTemperature':    ifbs(raw[b220101][17:18]),
            'batteryMinTemperature':    ifbs(raw[b220101][18:19]),
            'cumulativeEnergyCharged':  ifbu(raw[b220101][41:45]) / 10.0,
            'cumulativeEnergyDischarged': ifbu(raw[b220101][45:49]) / 10.0,
            'charging':                 1 if (charging_bits & 0xc) == 0x8 else 0,
            'normalChargePort':         1 if (charging_bits & 0x80) and raw[b220101][12] == 3 else 0,
            'rapidChargePort':          1 if (charging_bits & 0x80) and raw[b220101][12] != 3 else 0,
            'dcBatteryCurrent':         dc_battery_current,
            'dcBatteryPower':           dc_battery_current * dc_battery_voltage / 1000.0,
            'dcBatteryVoltage':         dc_battery_voltage,
            'soh':                      ifbu(raw[b220105][28:30]) / 10.0,
            # 'externalTemperature':      (raw[b220100][0x7ce][1][3] - 80) / 2.0,
            'odo':                      ffbu(raw[b22b002][11:15]) if b22b002 in raw else None,
        })

    def get_base_data(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }
