# EVNotiPi
Python Version of EVNotify

## Prerequisites
- Python 3
- Python Serial
- EVNotify API Python Library

## Installation
### Raspberry Pi
- `sudo apt-get update`
- `sudo apt-get upgrade`
- `sudo apt-get install bluetooth blueman bluez-tools python python-serial`
- `sudo bluetoothctl`
- (Plug OBD2 Dongle in car), eventually you also need to start the car
- `agent on`
- `scan on`
- (Wait, until Dongle is found, abort with CTRL+C)
- `pair <MAC-of-Dongle>`
- `trust <MAC-of-Dongle>`
- `sudo crontab -e` (insert the following and save: `@reboot rfcomm bind hci0 <MAC-of-Dongle> 1`
- `sudo reboot`
### EVNotiPi
- Copy `config.template.json` to `config.json`. Adjust the values for your needs
- Clone the EVNotify API Library (https://github.com/EVNotify/EVNotifyAPI).
- Create symbolic link from `EVNotifyAPI/libs/python/evnotify.py` to `evnotifyapi.py`
