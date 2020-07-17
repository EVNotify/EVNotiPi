import logging

class DUMMY:
    def __init__(self, config=None):
        self._log = logging.getLogger("EVNotiPi/DUMMY-Watchdog")

    def isCarAvailable(self):
        return True

    def getVoltage(self):
        return None

    def calibrateVoltage(self, realVoltage):
        pass
