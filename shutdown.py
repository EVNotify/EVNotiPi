#!/usr/bin/env python3

import RPi.GPIO as GPIO
from subprocess import call

PIN_12VOK = 20

GPIO.setmode(GPIO.BCM)

GPIO.setup(PIN_12VOK, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
try:
    while True:
        button1_state = GPIO.wait_for_edge(PIN_12VOK, GPIO.RISING, timeout=1000)
        if button1_state == False:
            print("12V failing! Shutdown!")
            call(['/bin/systemctl','poweroff'])
finally:
    GPIO.cleanup()
