""" Minimal watchdog module for testing """
import logging


class DUMMY:
    """ Watchdog class for testing """

    def __init__(self, config=None):
        self._log = logging.getLogger("EVNotiPi/DUMMY-Watchdog")

    def is_car_available(self):
        return True

    def get_voltage(self):
        return None

    def calibrate_voltage(self, realVoltage):
        pass
