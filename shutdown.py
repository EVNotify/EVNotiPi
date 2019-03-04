# This file needs to be start with root rights or as user pi with sudo at boot
#
#The script listens to GPIO 24 wheter the attached wemos pulls up D5 for shutting down the Rpi
#

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
while True: 
    if (GPIO.input(24) == True): 
        from subprocess import call
        call("sudo shutdown -h now", shell=True)
    time.sleep(1);
