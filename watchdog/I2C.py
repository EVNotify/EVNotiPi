""" Watchdog which we talk to through i2c """
from threading import Lock
import logging
from smbus import SMBus


class I2C:
    """ interface to i2c watchdog """
    def __init__(self, config):
        self.log = logging.getLogger("EVNotiPi/I2C-Watchdog")
        self.i2c_address = config['i2c_address']
        self.i2c_voltage_multiplier = 0.06
        self.i2c_bus_id = config['i2c_bus'] if 'i2c_bus' in config else 0
        self.i2c_bus = SMBus(self.i2c_bus_id)
        self.i2c_lock = Lock()

        if 'thresholds' in config:
            startup = config['thresholds'].get('startup')
            shutdown = config['thresholds'].get('shutdown')
            emergency = config['thresholds'].get('emergency')
            self.log.info("New thresholds startup(%s) shutdown(%s) emergency(%s)",
                          startup, shutdown, emergency)
            self.setThresholds(startup, shutdown, emergency)

    def _bus_open(self):
        self.i2c_lock.acquire()

    def _bus_close(self):
        self.i2c_lock.release()

    def is_car_available(self):
        """ Query the watchdog for car status """
        self._bus_open()
        self.i2c_bus.write_byte(self.i2c_address, 2)
        ret = self.i2c_bus.read_byte(self.i2c_address)
        self._bus_close()

        return ret == 0

    def get_voltage(self):
        """ Read the voltage of the watchdog's ADC """
        self._bus_open()
        self.i2c_bus.write_byte(self.i2c_address, 1)
        ret = self.i2c_bus.read_byte(self.i2c_address)
        self._bus_close()

        return ret * self.i2c_voltage_multiplier

    def calibrate_voltage(self, realVoltage):
        """ Adjust the conversion factor by providing an
            externally measured voltage. """
        self._bus_open()
        self.i2c_bus.write_byte(self.i2c_address, 1)
        ret = self.i2c_bus.read_byte(self.i2c_address)
        self._bus_close()

        self.i2c_voltage_multiplier = realVoltage / ret
        self.log.info("Calibration: %s %s %s", realVoltage,
                      ret, self.i2c_voltage_multiplier)

    def get_thresholds(self):
        """ Read the current thresholds. """
        self._bus_open()
        self.i2c_bus.write_byte(self.i2c_address, 0x11)
        start = self.i2c_bus.read_byte(self.i2c_address)
        self.i2c_bus.write_byte(self.i2c_address, 0x12)
        shut = self.i2c_bus.read_byte(self.i2c_address)
        self.i2c_bus.write_byte(self.i2c_address, 0x13)
        emerg = self.i2c_bus.read_byte(self.i2c_address)
        self._bus_close()

        return {
            'startup':   start * self.i2c_voltage_multiplier,
            'shutdown':  shut * self.i2c_voltage_multiplier,
            'emergency': emerg * self.i2c_voltage_multiplier,
        }

    def set_thresholds(self, startup=None, shutdown=None, emergency=None):
        """ Set new thresholds. """
        self._bus_open()

        if startup:
            self.i2c_bus.write_byte_data(self.i2c_address, 0x21,
                                         int(startup/self.i2c_voltage_multiplier))
        if shutdown:
            self.i2c_bus.write_byte_data(self.i2c_address, 0x22,
                                         int(shutdown/self.i2c_voltage_multiplier))
        if emergency:
            self.i2c_bus.write_byte_data(self.i2c_address, 0x23,
                                         int(emergency/self.i2c_voltage_multiplier))

        self._bus_close()
