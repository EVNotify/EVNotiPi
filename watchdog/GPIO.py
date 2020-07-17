import logging
import RPi.GPIO

class GPIO:
    def __init__(self, config):
        self._log = logging.getLogger("EVNotiPi/GPIO-Watchdog")
        self._shutdown_pin = config.get('shutdown_pin', 24)
        self._pup_down = config.get('pup_down', 21)
        RPi.GPIO.setmode(RPi.GPIO.BCM)
        RPi.GPIO.setup(self._shutdown_pin, RPi.GPIO.IN, pull_up_down=self._pup_down)

    def isCarAvailable(self):
        return RPi.GPIO.input(self._shutdown_pin) == 0

    def getVoltage(self):
        return None

    def calibrateVoltage(self, realVoltage):
        pass
