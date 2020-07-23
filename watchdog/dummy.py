""" Minimal watchdog module for testing """
import logging


class Dummy:
    """ Watchdog class for testing """

    def __init__(self, config=None):
        self._log = logging.getLogger("EVNotiPi/DUMMY-Watchdog")

    def is_car_available(self):
        return True
