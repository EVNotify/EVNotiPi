""" Watchdog reads a GPIO pin which signals if car is on """
import logging
import RPi.GPIO


class GPIO:
    """ Use a GPIO pin to get car status """

    def __init__(self, config):
        self._log = logging.getLogger("EVNotiPi/GPIO-Watchdog")
        self._shutdown_pin = config.get('shutdown_pin', 24)
        self._pup_down = config.get('pup_down', 21)
        RPi.GPIO.setmode(RPi.GPIO.BCM)
        RPi.GPIO.setup(self._shutdown_pin, RPi.GPIO.IN,
                       pull_up_down=self._pup_down)

    def is_car_available(self):
        """ Check if the pin has been pulled to ground """
        return RPi.GPIO.input(self._shutdown_pin) == 0

    def get_voltage(self):
        """ Dummy; GPIO has no voltage sensor available """
        return None

    def calibrate_voltage(self, realVoltage):
        """ No sensor, so no calibration """
