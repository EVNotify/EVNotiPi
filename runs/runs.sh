#!/bin/bash
date >> /tmp/logme
cd /var/www/html/evnotipi/
if pgrep -x "python3" > /dev/null
then
	
	if [[ $(find /tmp/lastrun -mmin  +5 -print) ]]; then
		killall python3
		sleep 3
		/usr/bin/python3 /var/www/html/evnotipi/evnotify.py &
		echo "killed and started" >> /tmp/logme
	else
		echo "not old enough" >> /tmp/logme	
	fi
else
	/usr/bin/python3 /var/www/html/evnotipi/evnotify.py &
	echo "started" >> /tmp/logme
fi
