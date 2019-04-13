#!/bin/bash
cd /var/www/html/PlugAndPlay
cp /var/www/html/PlugAndPlay/config.json /tmp/config.json
sudo git fetch origin
sudo git reset --hard origin/master
cp /tmp/config.json /var/www/html/PlugAndPlay/config.json 
chmod 777 /var/www/html/PlugAndPlay/config.json 
chmod +x /var/www/html/PlugAndPlay/runs/*.sh

