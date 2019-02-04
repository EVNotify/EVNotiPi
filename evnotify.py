import serial
import re
import time
import string
import io
import json
import importlib
import evnotifyapi
import IONIQ_BEV
import KONA_EV

# load config
with open('config.json', encoding='utf-8') as config_file:
    config = json.loads(config_file.read())

# load api lib
EVNotify = evnotifyapi.EVNotify(config['akey'], config['token'])

# establish serial port
ser = serial.Serial("/dev/rfcomm0", timeout=5)
ser.baudrate=9600
soc = 0

# available cars
class Cars:
    def __init__(self):
        self.IONIQ_BEV = IONIQ_BEV
        self.KONA_EV = KONA_EV

# instanciate the car instance
car = getattr((getattr(Cars(), EVNotify.getSettings()['car'])), EVNotify.getSettings()['car'])()
car.init()

curBytes = []
while True:
    for byte in ser.read():
        curBytes.append(byte)
        soc = car.parseData(curBytes)
        if soc > 0:
            curBytes = []
            car.requestData()
            EVNotify.setSOC(soc, soc)
            break