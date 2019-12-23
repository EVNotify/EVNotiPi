from dongle import *
from serial import Serial
from time import sleep
from threading import Lock
import pexpect
from pexpect import fdpexpect
from binascii import hexlify
import math
import RPi.GPIO as GPIO
import logging

class PiOBD2Hat:
    def __init__(self, dongle, watchdog = None):
        self.log = logging.getLogger("EVNotiPi/PiOBD2Hat")
        self.log.info("Initializing PiOBD2Hat")

        self.serial_lock = Lock()
        self.serial = Serial(dongle['port'], baudrate=dongle['speed'])
        self.exp = fdpexpect.fdspawn(self.serial)
        self.initDongle()

        self.config = dongle
        self.watchdog = watchdog
        if not watchdog:
            GPIO.setmode(GPIO.BCM)
            self.pin = dongle['shutdown_pin']
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=dongle['pup_down'])

        self.voltage_multiplier = 0.694

    def sendAtCmd(self, cmd, expect='OK'):
        cmd = bytes(cmd, 'utf-8')
        expect = bytes(expect, 'utf-8')
        try:
            with self.serial_lock:
                while self.serial.in_waiting:   # Clear the input buffer
                    self.log.warning("Stray data in buffer: " + \
                            str(self.serial.read(self.serial.in_waiting)))
                    sleep(0.2)
                self.log.debug("Send message: {}".format(self.cmd.hex()))
                self.exp.send(cmd + b'\r\n')
                self.exp.expect('>')
                ret = self.exp.before.strip(b'\r\n')
                self.log.debug("Received: {}".format(ret))
                if expect not in ret:
                    raise Exception('Expected %s, got %s' % (expect,ret))

        except pexpect.exceptions.TIMEOUT:
            ret = b'TIMEOUT'

        return ret.split(b"\r\n")[-1]

    def sendCommand(self, cmd):
        """
        @cmd: should be hex-encoded
        """
        cmd = hexlify(cmd)
        try:
            with self.serial_lock:
                while self.serial.in_waiting:   # Clear the input buffer
                    self.log.warning("Stray data in buffer: " + \
                            str(self.serial.read(self.serial.in_waiting)))
                    sleep(0.2)
                self.log.debug("Send message: {}".format(self.cmd.hex()))
                self.exp.send(cmd + b'\r\n')
                self.exp.expect('>')
                ret = self.exp.before.strip(b'\r\n')
                self.log.debug("Received: {}".format(ret))
        except pexpect.exceptions.TIMEOUT:
            ret = b'TIMEOUT'

        if ret in [b'NO DATA', b'TIMEOUT', b'CAN NO ACK']:
            raise NoData(ret)
        elif ret in [b'INPUT TIMEOUT', b'NO INPUT CHAR', b'UNKNOWN COMMAND',
                b'WRONG HEXCHAR COUNT', b'ILLEGAL COMMAND', b'SYNTAX ERROR',
                b'WRONG VALUE/RANGE', b'UNABLE TO CONNECT', b'BUS BUSY',
                b'NO FEEDBACK', b'NO SYNCBYTE', b'NO KEYBYTE',
                b'NO ADDRESSBYTE', b'WRONG PROTOCOL', b'DATA ERROR',
                b'CHECKSUM ERROR', b'NO ANSWER', b'COLLISION DETECT',
                b'CAN NO ANSWER', b'PRTOTOCOL 8 OR 9 REQUIRED',
                b'CAN ERROR']:
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

    def initDongle(self):
        cmds = [['ATRST','DIAMEX PI-OBD'],  # Cold start
                ['ATE0','OK'],              # Disable echo
                ['ATL1','OK'],              # Use \r\n
                ['ATOHS0','OK'],            # Disable space between HEX bytes
                ['ATH1','OK'],              # Display header
                ['ATST64','OK']]            # Input timeout (10 sec)

        for c,r in cmds:
            self.sendAtCmd(c, r)

    def setAllowLongMessages(self, value):
        #self.sendAtCmd('ATAL%i', value)
        return True

    def setProtocol(self, prot):
        if prot == 'CAN_11_500':
            self.sendAtCmd('ATP6','6 = ISO 15765-4, CAN (11/500)')
            self.sendAtCmd('ATONI1')   # No init sequence
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setCanID(self, can_id):
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, 'X')

        self.sendAtCmd('ATCT' + can_id)

    def setCANRxMask(self, mask):
        if isinstance(mask, bytes):
            mask = str(mask)
        elif isinstance(mask, int):
            mask = format(mask, 'X')

        self.sendAtCmd('ATCM' + mask)

    def setCANRxFilter(self, addr):
        if isinstance(addr, bytes):
            addr = str(addr)
        elif isinstance(addr, int):
            addr = format(addr, 'X')

        self.sendAtCmd('ATCR' + addr)

    def getObdVoltage(self):
        if self.watchdog:
            return round(self.watchdog.getVoltage(), 2)
        else:
            ret = self.sendAtCmd('AT!10','V')
            return round(float(ret[:-1]) * self.voltage_multiplier, 2)

    def isCarAvailable(self):
        if self.watchdog:
            return self.watchdog.getShutdownFlag() == 0
        else:
            #return self.getObdVoltage() > 13.0
            return GPIO.input(self.pin) == False

    def calibrateObdVoltage(self, realVoltage):
        if self.watchdog:
            self.watchdog.calibrateVoltage(realVoltage)
        else:
            ret = self.sendAtCmd('AT!10','V')
            self.voltage_multiplier = realVoltage / float(ret[:-1])

