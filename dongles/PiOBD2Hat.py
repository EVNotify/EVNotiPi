from serial import Serial
import pexpect
from pexpect import fdpexpect

class PiOBD2Hat:

    class CAN_ERROR(Exception): pass
    class NO_DATA(Exception): pass

    def __init__(self, dongle):
        print("Init Dongle")
        self.serial = Serial(dongle['port'], baudrate=dongle['speed'], timeout=5)
        self.exp = fdpexpect.fdspawn(self.serial.fd)
        self.initDongle()

    def sendAtCmd(self, cmd, expect='OK'):
        expect = bytes(expect, 'utf-8')
        cmd = bytes(cmd, 'utf-8')

        try:
            self.exp.send(cmd + b'\r\n')
            self.exp.expect('>', timeout=5)
            ret = self.exp.before.strip(b'\r\n')

            if expect not in ret:
                raise Exception('Expected %s, got %s' % (expect,ret))

        except pexpect.exceptions.TIMEOUT:
            ret = b'TIMEOUT'

    def sendCommand(self, cmd):
        cmd = bytes(cmd, 'utf-8')
        print("Send Command "+str(cmd))
        try:
            self.exp.send(cmd + b'\r\n')
            self.exp.expect('>', timeout=5)
            ret = self.exp.before.strip(b'\r\n')
            print(ret)
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
            raise PiOBD2Hat.CAN_ERROR(ret)

        try:
            raw = {}
            for line in ret.split(b'\r\n'):
                value = bytes.fromhex(str(line[5:],'ascii'))
                if value == b'\x00\x00\x00\x00\x00\x00\x00':
                    raise ValueError
	
	        raw[int(line[:5],16)] = value                
        except ValueError:
            raise PiOBD2Hat.CAN_ERROR(ret)

        return raw

    def initDongle(self):
        cmds = [['ATZ','DIAMEX PI-OBD'],
                ['ATE0','OK'],
                ['ATL1','OK'],
                ['ATOHS0','OK'],
                ['ATH1','OK'],
                ['ATSTFF','OK']]

        for c,r in cmds:
            self.sendAtCmd(c, r)

    def setAllowLongMessages(self, value):
        #self.sendAtCmd('ATAL%i', value)
        return True

    def setProtocol(self, prot):
        if prot == 'CAN_11_500':
            self.sendAtCmd('ATP6','6 = ISO 15765-4, CAN (11/500)')
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setIDFilter(self, filter):
        self.sendAtCmd('ATSF' + str(filter))

    def setCANRxMask(self, mask):
        self.sendAtCmd('ATCM' + str(mask))

    def setCANRxFilter(self, addr):
        self.sendAtCmd('ATCR' + str(addr))


