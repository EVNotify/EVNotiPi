""" Module for the Renault Zoe Z.E.50 """
from .car import Car, ifbu

cmd_auxVoltage = bytes.fromhex('222005')   # PR252
cmd_chargeState = bytes.fromhex('225017')   # ET018
cmd_soc = bytes.fromhex('229001')
cmd_soc_bms = bytes.fromhex('229002')
cmd_voltage = bytes.fromhex('229006')
cmd_bms_energy = bytes.fromhex('2291C8')   # PR155
cmd_odo = bytes.fromhex('2291CF')   # PR046 ?? 0x80000225 => 17km ?
cmd_nrg_discharg = bytes.fromhex('229245')   # PR047
cmd_current = bytes.fromhex('229257')   # PR218
cmd_soh = bytes.fromhex('22927A')   # ET148


class ZoeZe50(Car):
    """ Class for Zoe ZE50 """
    def __init__(self, config, dongle, watchdog, gps):
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_29_500')

    def read_dongle(self, data):
        """ Read and parse data from dongle """
        def bms(cmd):
            return self._dongle.send_command_ex(cmd, canrx=0x18DAF1DB, cantx=0x18DADBF1)[3:]

        data.update(self.get_base_data())

        dc_battery_current = ifbu(bms(cmd_current)) - 32768
        dc_battery_voltage = ifbu(bms(cmd_voltage)) / 1000

        # soh_raw = bms(cmd_soh) # returns 254 bytes of data ...

        cell_volts = []
        for i in range(0x21, 0x84):
            cmd = bytes.fromhex("2290%02x" % (i))
            cell_volts.append(ifbu(bms(cmd)) / 1000)

        module_temps = []
        for i in range(0x31, 0x3d):
            cmd = bytes.fromhex("2291%02x" % (i))
            module_temps.append(ifbu(bms(cmd)) / 10 - 60)

        data.update({
            # Base
            'SOC_BMS':              ifbu(bms(cmd_soc_bms)) / 100,
            'SOC_DISPLAY':          ifbu(bms(cmd_soc)) / 100,

            # Extended:
            'auxBatteryVoltage':    ifbu(bms(cmd_auxVoltage)) / 100.0,

            # 'batteryInletTemperature':
            'batteryMaxTemperature': max(module_temps),
            'batteryMinTemperature': min(module_temps),

            'cumulativeEnergyCharged':  ifbu(bms(cmd_bms_energy)) / 1000.0,
            'cumulativeEnergyDischarged': ifbu(bms(cmd_nrg_discharg)) / 1000.0,

            'charging':             0 if ifbu(bms(cmd_chargeState)) == 0 else 1,
            # 'normalChargePort':
            # 'rapidChargePort':

            'dcBatteryCurrent':     dc_battery_current,
            'dcBatteryPower':       dc_battery_current * dc_battery_voltage / 1000.0,
            'dcBatteryVoltage':     dc_battery_voltage,

            # 'soh':
            # 'externalTemperature':
            # 'odo':                  ifbu(bms(cmd_odo)),
        })

        for i, cvolt in enumerate(cell_volts):
            key = "cellVoltage%02d" % (i+1)
            data[key] = float(cvolt)

        for i, temp in enumerate(module_temps):
            key = "cellTemp%02d" % (i+1)
            data[key] = float(temp)

    def get_base_data(self):
        return {
            "CAPACITY": 50,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 50.0
        }
