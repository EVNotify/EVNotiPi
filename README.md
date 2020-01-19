# EVNotiPi
Python Version of EVNotify
## Needed Hardware
- Raspberry Pi Zero W with GPIO Header https://buyzero.de/collections/boards-kits/products/raspberry-pi-zero-w-easy-mit-bestucktem-header
- OTG cable for Raspberry Pi https://buyzero.de/collections/raspberry-kabel-und-adapter/products/micro-usb-zu-usb-otg-adapter
- small wires in different colors: https://www.amazon.de/AZDelivery-Jumper-Arduino-Raspberry-Breadboard/dp/B07KYHBVR7?tag=gplay97-21
- 4 screws M2,5x15 (to fix the OBD-Hat into the case)
- 5 screws M2,5x8 self-cutting (for the case)
- LTE Stick Huawai E3372 https://www.amazon.de/gp/product/B011BRKPLE?tag=gplay97-21
- A case, for example https://github.com/noradtux/evnotipi-case
- The i2c watchdog and power supply, https://github.com/noradtux/evnotipi-watchdog
### Variant 1 (MCP2515 based adapter with GPS); Recommended:
- PiCan2 with GPS: https://buyzero.de/products/pican-2-mit-gps / http://skpang.co.uk/catalog/pican-with-gps-canbus-board-for-raspberry-pi-23-p-1520.html
- µFL to SMA: http://skpang.co.uk/catalog/interface-cable-sma-to-ufl-p-551.html / https://www.amazon.de/Adafruit-u-FL-Adapter-Cable-ADA851/dp/B00XW2LKNO?tag=gplay97-21
- Active external GPS antenna: http://skpang.co.uk/catalog/gps-antenna-with-sma-male-connector-p-236.html / https://www.amazon.de/Adafruit-GPS-Antenna-External-Active/dp/B01M0QB38R?tag=gplay97-21
### Variant 2 (MCP2515 based adapter without GPS):
- PiCan2: https://buyzero.de/products/pican-2 / http://skpang.co.uk/catalog/pican2-canbus-board-for-raspberry-pi-2-p-1475.html
- Long Header Extender: http://skpang.co.uk/catalog/2x20pin-header-extender-with-105mm-pins-p-1500.html
### Variant 2.1 (additional external GPS):
- External GPS: https://www.amazon.de/Adafruit-Channels-GPS-Empfänger-Modul-145-dBmW-66-Channels-blau/dp/B01H1R8BK0?tag=gplay97-21
### Variant 3 (Diamex OBD-Hat, the old default; does not support Renault Zoe):
- Diamex OBD-Hat: https://www.diamex.de/dxshop/PI-OBD-HAT-OBD2-Modul-fuer-Raspberry-PI with flat connector
## Wiring
### OBD2 connection
The case has a slot for a DB9 plug (the side with the pins). Connect the DB9 plug to CAN_H and CAN_L of the CAN-hat; connect GND and 12V to the watchdog. Pinout is as follows:
```
OBD2        DB9
4,5  GND    1,2
  6  CAN_H  3
 14  CAN_L  5
 16  12V    9
```
This pinout should be compatible to most DB9 to OBD2 cables. One can always build one's own cable, though.
## Installation
### Raspberry Pi
- sudo apt update
- sudo apt upgrade
- sudo apt install python3-{pip,rpi.gpio,serial,requests,sdnotify,pyroute2,smbus,yaml,gevent} gpsd watchdog rsyslog-
- sudo systemctl disable --now serial-getty@ttyAMA0.service
- sudo sed -i -re "\\$agpu_mem=16\nmax_usb_current=1\nenable_uart=1\ndtoverlay=disable-bt\ndtoverlay=gpio-poweroff:active_low" -e "/^dtparam=audio=/ s/^/#/" /boot/config.txt
- sudo sed -i -re '/console=/ s/$/ panic=1/' /boot/cmdline.txt
- sudo sed -i -re '/max-load/ s/^#//' /etc/watchdog.conf
- sudo sed -i -re "\\$adtparam=watchdog=on" /boot/config.txt
#### If using MCP2515 based adapter:
- sudo apt install dkms
- sudo git clone https://github.com/noradtux/can-isotp /usr/src/can-isotp
- sudo dkms add /usr/src/can-isotp
- sudo dkms install -m can-isotp -v r26.ced84ca
- sudo sed -i -re "\\$adtparam=spi=on\ndtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25\ndtoverlay=spi-bcm2835-overlay" /boot/config.txt
- echo -e "[Match]\nDriver=mcp251x\n\n[CAN]\nBitRate=500000\nRestartSec=100ms" | sudo tee /etc/systemd/network/can.network
- sudo systemctl enable --now systemd-networkd
#### If using the i2c watchdog (the one with the Trinket M0):
- sudo sed -i -re "\\$adtparam=i2c_arm=on,i2c_arm_baudrate=50000" /boot/config.txt
- sudo sed -i -re "\\$ai2c-dev" /etc/modules
### EVNotiPi
- sudo git clone --recurse-submodules https://github.com/EVNotify/EVNotiPi /opt/evnotipi
- cd /opt/evnotipi
- sudo pip3 install -r requirements.txt
- sudo systemctl link /opt/evnotipi/evnotipi.service
- sudo systemctl enable evnotipi.service
- sudo systemctl disable evnotipi_shutdown.{timer,service} # if updating
- sudo cp config.yaml.template config.yaml
#### Edit config, follow comments in the file
- sudo nano config.yaml # nano or any other editor

