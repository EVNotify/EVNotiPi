from smbus import SMBus
from threading import Lock
import logging

class Watchdog:
    def __init__(self, config):
        self.log = logging.getLogger("EVNotiPi/Watchdog")
        self.i2c_address = config['i2c_address']
        self.i2c_voltage_multiplier = 0.06
        self.i2c_bus_id = config['i2c_bus'] if 'i2c_bus' in config else 0
        self.i2c_bus = SMBus(self.i2c_bus_id)
        self.i2c_lock = Lock()

        if 'thresholds' in config:
            startup = config['thresholds']['startup'] if 'startup' in config['thresholds'] else None
            shutdown = config['thresholds']['shutdown'] if 'shutdown' in config['thresholds'] else None
            emergency = config['thresholds']['emergency'] if 'emergency' in config['thresholds'] else None
            self.log.info("New thresholds startup(%s) shutdown(%s) emergency(%s)", startup, shutdown, emergency)
            self.setThresholds(startup, shutdown, emergency)

    def _BusOpen(self):
        self.i2c_lock.acquire()
        # self.i2c_bus.open()

    def _BusClose(self):
        # self.i2c_bus.close()
        self.i2c_lock.release()

    def getShutdownFlag(self):
        self._BusOpen()
        self.i2c_bus.write_byte(self.i2c_address, 2)
        ret = self.i2c_bus.read_byte(self.i2c_address)
        self._BusClose()

        return ret

    def getVoltage(self):
        self._BusOpen()
        self.i2c_bus.write_byte(self.i2c_address, 1)
        ret = self.i2c_bus.read_byte(self.i2c_address)
        self._BusClose()

        return ret * self.i2c_voltage_multiplier

    def calibrateVoltage(self, realVoltage):
        self._BusOpen()
        self.i2c_bus.write_byte(self.i2c_address, 1)
        ret = self.i2c_bus.read_byte(self.i2c_address)
        self._BusClose()

        self.i2c_voltage_multiplier = realVoltage / ret
        self.log.info("Calibration: {} {} {}".format(realVoltage, ret, self.i2c_voltage_multiplier))

    def getThresholds(self):
        self._BusOpen()
        self.i2c_bus.write_byte(self.i2c_address, 0x11)
        start = self.i2c_bus.read_byte(self.i2c_address)
        self.i2c_bus.write_byte(self.i2c_address, 0x12)
        shut = self.i2c_bus.read_byte(self.i2c_address)
        self.i2c_bus.write_byte(self.i2c_address, 0x13)
        emerg = self.i2c_bus.read_byte(self.i2c_address)
        self._BusClose()

        return {
                'startup': start * self.i2c_voltage_multiplier,
                'shutdown': shut * self.i2c_voltage_multiplier,
                'emergency': emerg * self.i2c_voltage_multiplier,
                }

    def setThresholds(self, startup=None, shutdown=None, emergency=None):
        self._BusOpen()

        if startup:
            self.i2c_bus.write_byte_data(self.i2c_address, 0x21, int(startup / self.i2c_voltage_multiplier))
        if shutdown:
            self.i2c_bus.write_byte_data(self.i2c_address, 0x22, int(shutdown / self.i2c_voltage_multiplier))
        if emergency:
            self.i2c_bus.write_byte_data(self.i2c_address, 0x23, int(emergency / self.i2c_voltage_multiplier))

        self._BusClose()


if __name__ == '__main__':
    config = {
            'enable': True,
            'i2c_address': 8,
            'i2c_bus': 1,
            'thresholds': {
                'startup': 13.0,
                'shutdown': 12.6
                }
            }

    wd = Watchdog(config)

    print(wd.getShutdownFlag(),
            wd.getVoltage(),
            wd.getThresholds())
