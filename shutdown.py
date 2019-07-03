#!/usr/bin/env python3

import RPi.GPIO as GPIO
from subprocess import call
from time import sleep

PIN_12VOK = 20
MAX_FAIL = 10
fail_cnt = 0

GPIO.setmode(GPIO.BCM)

GPIO.setup(PIN_12VOK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
try:
    while True:
        #button1_state = GPIO.wait_for_edge(PIN_12VOK, GPIO.RISING, timeout=1000)
        button1_state = GPIO.input(PIN_12VOK)
        #print(button1_state,fail_cnt)
        if button1_state == 1 and fail_cnt < MAX_FAIL :
            fail_cnt += 1
        elif fail_cnt > 0:
            fail_cnt -= 1

        if fail_cnt >= MAX_FAIL:
            print("12V failing! Shutdown!")
            call(['/bin/systemctl','poweroff'])
            sleep(5)

        sleep(1)
finally:
    GPIO.cleanup()
