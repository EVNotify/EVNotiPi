from serial import Serial
from pexpect import fdpexpect

class CAN_ERROR(Exception): pass

class PiOBD2Hat:

    def __init__(self, dongle):
        print("Init Dongle")
        self.serial = Serial(dongle['port'], baudrate=dongle['speed'], timeout=5)
        self.exp = fdpexpect.fdspawn(self.serial.fd)
        self.initDongle()

    def sendAtCmd(self, cmd, expect='OK'):
        expect = bytes(expect, 'utf-8')
        cmd = bytes(cmd, 'utf-8')

        self.exp.send(cmd + b'\r\n')
        self.exp.expect('>')
        ret = self.exp.before.strip(b'\r\n')

        if expect not in ret:
            raise Exception('Expected %s, got %s' % (expect,ret))

    def sendCommand(self, cmd):
        cmd = bytes(cmd, 'utf-8')
        print("Send Command "+str(cmd))
        self.exp.send(cmd + b'\r\n')
        self.exp.expect('>')
        ret = self.exp.before.strip(b'\r\n')
        if ret == b'CAN NO ACK':
            raise CAN_ERROR(ret)

        return ret.split(b'\r\n')

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

