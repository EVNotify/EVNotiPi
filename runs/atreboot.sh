#!/bin/bash
#listener for powering off
echo 0 > /tmp/eth0broken
python /var/www/html/PlugAndPlay/shutdown.py &
python3 /var/www/html/PlugAndPlay/evnotipi.py &




