# PlugAndPlay


crontab:


@reboot sleep 10 && var/www/html/evnotipi/runs/atreboot.sh
* * * * * /var/www/html/evnotipi/runs/runs.sh &
