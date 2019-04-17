#!/bin/bash
cd /var/www/html/PlugAndPlay
sudo cp /var/www/html/PlugAndPlay/config.json /tmp/config.json
sudo git fetch origin
sudo git reset --hard origin/stable
sudo cp /tmp/config.json /var/www/html/PlugAndPlay/config.json 
sudo chmod 777 /var/www/html/PlugAndPlay/config.json 
sudo chmod 777 /var/www/html/PlugAndPlay/runs/update.sh
sudo chmod +x /var/www/html/PlugAndPlay/runs/*.sh
uuid=$(</sys/class/net/eth0/address)
curl -s -d "update="PlugAndPlay$uuid"" -H "Content-Type: application/x-www-form-urlencoded" -X POST http://openwb.de/tools/update.php
sudo cp web/update.html ../
sudo cp web/update.php ../
sudo cp web/indexmain.html ../index.html
