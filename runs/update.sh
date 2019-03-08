#!/bin/bash
cp /var/www/html/evnotify/config.json /tmp/config.json
sudo git fetch origin
sudo git fetch --hard origin/master
cp /tmp/config.json /var/www/html/evnotify/config.json 
chmod 777 /var/www/html/evnotify/config.json 

