# EVNotiPi
Python Version of EVNotify

## Needed Hardware
- Diamex OBD-Hat  https://www.diamex.de/dxshop/PI-OBD-HAT-OBD2-Modul-fuer-Raspberry-PI with flat connector
- Raspberry Pi Zero W
- DC/DC Step-Down Converter  https://www.aliexpress.com/item/5-pcs-Ultra-Small-Size-DC-DC-Step-Down-Power-Supply-Module-3A-Adjustable-Step-Down/32261885063.html?spm=a2g0s.9042311.0.0.57094c4dLTzDDA
- Wemos D1 mini  https://www.aliexpress.com/item/D1-mini-Mini-NodeMcu-4M-bytes-Lua-WIFI-Internet-of-Things-development-board-based-ESP8266/32529101036.html?spm=a2g0x.10010108.1000001.12.71c46d4fQAgD9Q
- Wemos Ralay Shield  https://www.aliexpress.com/item/1PCS-NEW-Relay-Shield-for-Arduino-WeMos-D1-Mini-ESP8266-Development-Board-WeMos-D1-Relay-Module/32737849680.html?spm=a2g0o.productlist.0.0.2aae2b26AhbDEs&ws_ab_test=searchweb0_0%2Csearchweb201602_10%2Csearchweb201603_52&algo_pvid=5e7c779b-c82a-480b-bdb6-50121bd34f8a&btsid=84c71f9f-6e18-48a9-8f54-6813abeee7ff&algo_expid=5e7c779b-c82a-480b-bdb6-50121bd34f8a-0
- Case printed with PETG  http.....

## Prerequisites
- Python 3
- Python Serial
- Python GPS
- GPSd
- EVNotify API Python Library

## Installation
### Raspberry Pi
- `sudo apt-get update`
- `sudo apt-get upgrade`
- `sudo apt-get install python python-serial python-gps gpsd`
### EVNotiPi
- Copy `config.template.json` to `config.json`. Adjust the values for your needs

