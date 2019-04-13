#!/bin/bash
cd /var/www/html/PlugAndPlay
cp /var/www/html/PlugAndPlay/config.json /tmp/config.json
sudo git fetch origin
sudo git reset --hard origin/master
cp /tmp/config.json /var/www/html/PlugAndPlay/config.json 
chmod 777 /var/www/html/PlugAndPlay/config.json 
chmod +x /var/www/html/PlugAndPlay/runs/*.sh
uuid=$(</sys/class/net/eth0/address)
curl -d "plugandplay="$uuid"" -H "Content-Type: application/x-www-form-urlencoded" -X POST http://openwb.de/tools/update.php
