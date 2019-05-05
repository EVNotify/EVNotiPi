from serial import Serial
from time import sleep
import pexpect
from pexpect import fdpexpect

class PiOBD2Hat:

    class CAN_ERROR(Exception): pass
    class NO_DATA(Exception): pass

    def __init__(self, dongle):
        print("Init Dongle")
        self.serial = Serial(dongle['port'], baudrate=dongle['speed'])
        self.exp = fdpexpect.fdspawn(self.serial)
        self.initDongle()

    def sendAtCmd(self, cmd, expect='OK'):
        cmd = bytes(cmd, 'utf-8')
        expect = bytes(expect, 'utf-8')
        try:
            while self.serial.in_waiting:   # Clear the input buffer
                print("Stray data in buffer: " + \
                        str(self.serial.read(self.serial.in_waiting)))
                sleep(0.2)
            self.exp.send(cmd + b'\r\n')
            self.exp.expect('>')
            ret = self.exp.before.strip(b'\r\n')
            if expect not in ret:
                raise Exception('Expected %s, got %s' % (expect,ret))

        except pexpect.exceptions.TIMEOUT:
            ret = b'TIMEOUT'

        return ret.split(b"\r\n")[-1]

    def sendCommand(self, cmd):
        cmd = bytes(cmd, 'utf-8')
        try:
            while self.serial.in_waiting:   # Clear the input buffer
                print("Stray data in buffer: " + \
                        str(self.serial.read(self.serial.in_waiting)))
                sleep(0.2)
            self.exp.send(cmd + b'\r\n')
            self.exp.expect('>')
            ret = self.exp.before.strip(b'\r\n')
        except pexpect.exceptions.TIMEOUT:
            ret = b'TIMEOUT'

        if ret in [b'NO DATA', b'TIMEOUT', b'CAN NO ACK']:
            raise PiOBD2Hat.NO_DATA(ret)
        elif ret in [b'INPUT TIMEOUT', b'NO INPUT CHAR', b'UNKNOWN COMMAND',
                b'WRONG HEXCHAR COUNT', b'ILLEGAL COMMAND', b'SYNTAX ERROR',
                b'WRONG VALUE/RANGE', b'UNABLE TO CONNECT', b'BUS BUSY',
                b'NO FEEDBACK', b'NO SYNCBYTE', b'NO KEYBYTE',
                b'NO ADDRESSBYTE', b'WRONG PROTOCOL', b'DATA ERROR',
                b'CHECKSUM ERROR', b'NO ANSWER', b'COLLISION DETECT',
                b'CAN NO ANSWER', b'PRTOTOCOL 8 OR 9 REQUIRED',
                b'CAN ERROR']:
            raise PiOBD2Hat.CAN_ERROR("Failed Command {}\n{}".format(cmd,ret))

        try:
            raw = {}
            for line in ret.split(b'\r\n'):
                if len(line) != 19:
                    raise ValueError
                raw[int(line[:5],16)] = bytes.fromhex(str(line[5:],'ascii'))
        except ValueError:
            raise PiOBD2Hat.CAN_ERROR("Failed Command {}\n{}".format(cmd,ret))

        return raw

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
            self.sendAtCmd('ATONI1','OK')   # No init sequence
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setIDFilter(self, filter):
        self.sendAtCmd('ATSF' + str(filter))

    def setCANRxMask(self, mask):
        self.sendAtCmd('ATCM' + str(mask))

    def setCANRxFilter(self, addr):
        self.sendAtCmd('ATCR' + str(addr))

    def getObdVoltage(self):
        ret = self.sendAtCmd('AT!10','V')
        return float(ret[:-1]) # strip the 'V'

