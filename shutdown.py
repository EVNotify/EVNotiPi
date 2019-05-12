# This file needs to be start with root rights or as user pi with sudo at boot
#
#The script listens to GPIO 22 wheter the attached wemos pulls up D5 for shutting down the Rpi
#
# ToDo: atreboot handler should be written

import RPi.GPIO as GPIO
import time
from subprocess import call
GPIO.setmode(GPIO.BCM)

GPIO.setup(24, GPIO.IN)
while True: 
    if (GPIO.input(24) == True): 
        from subprocess import call
        call("sudo shutdown -h now", shell=True)
    time.sleep(1);



