# This file needs to be start with root rights or as user pi with sudo at boot
#
#The script listens to GPIO 22 wheter the attached wemos pulls up D5 for shutting down the Rpi
#
# ToDo: atreboot handler should be written

import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP)
try:
    while True:
        button1_state = GPIO.input(22)
        time.sleep(1)
        if button1_state == False:
            from subprocess import call
            call("sudo shutdown -h now", shell=True)
except:
    GPIO.cleanup()
