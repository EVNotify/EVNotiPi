#!/bin/bash
#listener for powering off
echo 0 > /tmp/eth0broken
python /var/www/html/EVNotiPi/shutdown.py &
python3 /var/www/html/EVNotiPi/evnotipi.py &




