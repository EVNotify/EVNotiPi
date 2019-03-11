# This file needs to be start with root rights or as user pi with sudo at boot
#
#The script listens to GPIO 22 wheter the attached wemos pulls up D5 for shutting down the Rpi
#
# ToDo: atreboot handler should be written

import RPi.GPIO as GPIO
import time
from subprocess import call

PIN_12VOK = 24

GPIO.setmode(GPIO.BCM)

GPIO.setup(PIN_12VOK, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
try:
    while True:
        button1_state = GPIO.wait_for_edge(PIN_12VOK, GPIO.RISING)
        if button1_state == False:
            call("sudo shutdown -h now", shell=True)
finally:
    GPIO.cleanup()
