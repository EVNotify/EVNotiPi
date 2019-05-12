#!/bin/bash
date >> /tmp/logme
<<<<<<< HEAD
cd /var/www/html/EVNotiPi/
if ! pgrep -x "python3" > /dev/null
then
	/usr/bin/python3 /var/www/html/EVNotiPi/evnotipi.py &
	echo "started" >> /tmp/logme
fi
if [ ! -d "/sys/class/net/eth0" ]; then
	date >> /var/log/evnotipi.log
	echo "is broken" >> /var/log/evnotipi.log
	eth0stat=$(</tmp/eth0broken)
	if (( eth0stat == 1 )) ; then
		echo "reboot now" >> /var/log/evnotipi.log
		/sbin/reboot
	fi
	echo "timer to 1" >> /var/log/evnotipi.log
	echo 1 > /tmp/eth0broken
else
	echo 0 > /tmp/eth0broken
=======
cd /var/www/html/PlugAndPlay/
if ! pgrep -x "python3" > /dev/null
then
        /usr/bin/python3 /var/www/html/PlugAndPlay/evnotipi.py &
        echo "started" >> /tmp/logme
fi
if [ ! -d "/sys/class/net/eth0" ]; then
        date >> /var/log/evnotipi.log
        echo "is broken" >> /var/log/evnotipi.log
        eth0stat=$(</tmp/eth0broken)
        if (( eth0stat == 1 )) ; then
                echo "reboot now" >> /var/log/evnotipi.log
                /sbin/reboot
        fi
        echo "timer to 1" >> /var/log/evnotipi.log
        echo 1 > /tmp/eth0broken
else
        echo 0 > /tmp/eth0broken
>>>>>>> origin/stable
fi
