from dongle import *
import serial
from threading import Lock
from time import sleep
import math
import RPi.GPIO as GPIO
import logging

class ATBASE:
    def __init__(self, dongle, watchdog = None):
        self.log = logging.getLogger("EVNotiPi/{}".format(__name__))
        self.log.info("Initializing PiOBD2Hat")

        self.serial_lock = Lock()
        self.serial = serial.Serial(dongle['port'], baudrate=dongle['speed'], timeout=1)
        self.initDongle()

        self.config = dongle
        self.watchdog = watchdog
        if not watchdog:
            GPIO.setmode(GPIO.BCM)
            self.pin = dongle['shutdown_pin']
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=dongle['pup_down'])

        self.current_canid = 0
        self.current_canfilter = 0
        self.current_canmask = 0

    def talkToDongle(self, cmd, expect=None):
        try:
            with self.serial_lock:
                while self.serial.in_waiting:   # Clear the input buffer
                    self.log.warning("Stray data in buffer: " + \
                            str(self.serial.read(self.serial.in_waiting)))
                    sleep(0.1)

                self.log.debug("Send command: {}".format(cmd))
                self.serial.write(bytes(cmd + '\r\n', 'ascii'))
                ret = bytearray()
                while True:
                    if not self.serial.in_waiting:
                        sleep(0.1)
                        continue
                    data = self.serial.read(self.serial.in_waiting)

                    endidx = data.find(b'>')
                    if endidx >= 0:
                        ret.extend(data[:endidx])
                        break
                    else:
                        ret.extend(data)

                self.log.debug("Received: {}".format(ret))

                if expect:
                    expect = bytes(expect, 'ascii')
                    if expect not in ret:
                        raise Exception("Expected {}, got {}".format(expect,ret))

        except serial.SerialTimeoutException:
            ret = b'TIMEOUT'

        return ret.strip(b'\r\n')

    def sendAtCmd(self, cmd, expect=None):
        ret = self.talkToDongle(cmd, expect)
        return ret.split(b"\r\n")[-1]

    def sendCommand(self, cmd):
        """
        @cmd: bytes or bytearray containing command bytes
        """
        cmd = cmd.hex()
        ret = self.talkToDongle(cmd)

        if ret in this.ret_NoData:
            raise NoData(ret)
        elif ret in self.ret_CanError:
            raise CanError("Failed Command {}\n{}".format(cmd,ret))

        try:
            data = {}
            raw = ret.split(b'\r\n')
            lines = None

            for line in raw:
                if len(line) != 19:
                    raise ValueError

                identifier = int(line[0:3],16)
                frame_type = int(line[3:4],16)

                if frame_type == 0:     # Single frame
                    idx = 0
                    lines = 1
                elif frame_type == 1:   # First frame
                    lines = math.ceil((int.from_bytes(bytes.fromhex(str(b'0' + line[4:7], 'ascii')),
                        byteorder='big', signed=False) + 1) / 7)
                    idx = 0
                    if len(raw) != lines:
                        raise ValueError
                elif frame_type == 2:   # Consecutive frame
                    idx = int(line[4:5],16)
                else:                   # Unexpected frame
                    raise ValueError

                if not identifier in data:
                    data[identifier] = [None] * lines

                data[identifier][idx] = bytes.fromhex(str(line[5:],'ascii'))

            # Check if all entries are filled
            for key, val in data.items():
                for i in val:
                    if i == None:
                        raise ValueError

        except ValueError:
            raise CanError("Failed Command {}\n{}".format(cmd,ret))

        return data

    def sendCommandEx(self, cmd, cantx, canrx):
        cmd = cmd.hex()
        self.setCanID(cantx)
        self.setCANRxFilter(canrx)
        self.setCANRxMask(0x1fffffff if self.is_extended else 0x7ff)

        ret = self.talkToDongle(cmd)

        if ret in self.ret_NoData:
            raise NoData(ret)
        elif ret in self.ret_CanError:
            raise CanError("Failed Command {}\n{}".format(cmd,ret))

        try:
            data = None
            data_len = 0
            last_idx = 0
            raw = str(ret,'ascii').split('\r\n')

            #self.log.debug(raw)
            for line in raw:
                if (self.is_extended == False and len(line) != 19) \
                        or (self.is_extended == True and len(line) != 27):
                    raise ValueError

                if self.is_extended:
                    offset = 8
                else:
                    offset = 3

                identifier = int(line[0:offset], 16)
                frame_type = int(line[offset:offset+1], 16)

                if frame_type == 0:     # Single frame
                    self.log.debug("{} single frame".format(line))
                    data_len = int(line[offset+1:offset+2], 16)
                    data = bytes.fromhex(line[offset+2:data_len*2+offset+2])
                    break

                elif frame_type == 1:   # First frame
                    self.log.debug("{} first frame".format(line))
                    data_len = int(line[offset+1:offset+4], 16)
                    data = bytearray.fromhex(line[offset+4:])
                    last_idx = 0

                elif frame_type == 2:   # Consecutive frame
                    self.log.debug("{} consecutive frame".format(line))
                    idx = int(line[offset+1:offset+2], 16)
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx({}) idx({})".format(last_idx,idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(bytearray.fromhex(line[offset+2:frame_len*2+offset+2]))
                    last_idx = idx

                    if data_len == len(data):
                        break

                else:                   # Unexpected frame
                    raise ValueError

            if not data or data_len == 0:
                raise NoData('NO DATA')
            if data_len != len(data):
                raise CanError("Data length mismatch {}: {} vs {} {}".format(cmd, data_len, len(data), data.hex()))

        except ValueError:
            raise CanError("Failed Command {}\n{}".format(cmd,ret))

        return data

    def isCarAvailable(self):
        if self.watchdog:
            return self.watchdog.getShutdownFlag() == 0
        else:
            #return self.getObdVoltage() > 13.0
            return GPIO.input(self.pin) == False

