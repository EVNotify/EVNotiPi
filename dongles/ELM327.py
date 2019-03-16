from serial import Serial
import logging
from pexpect import fdpexpect

class ELM327:

    def __init__(self, dongle):
        self.serial = Serial(dongle['port'], baudrate=dongle['speed'], timeout=5)
        self.exp = fdpexpect.fdspawn(self.serial.fd)
        self.initDongle()

    def sendAtCmd(self, cmd, expect='OK'):
        expect = bytes(expect, 'utf-8')
        cmd = bytes(cmd, 'utf-8')

        logging.info('Write %s' % str(cmd))
        self.exp.send(cmd + b'\r\n')
        self.exp.expect('>')
        ret = self.exp.before.strip(b'\r\n')
        logging.debug('Got %s' % str(cmd))
        if expect not in ret:
            raise Exception('Expected %s, got %s' % (expect,ret))

    def sendCommand(self, cmd):
        cmd = bytes(cmd, 'utf-8')
        logging.info('Write %s' % str(cmd))
        self.exp.send(cmd + b'\r\n')
        self.exp.expect('>')
        return self.exp.before.strip(b'\r\n').split(b'\r\n')

    def initDongle(self):
        cmds = [['ATZ','OK'],
                ['ATE0','OK'],
                ['ATL1','OK'],
                ['ATS0','OK'],
                ['ATH1','OK'],
                ['ATSTFF','OK'],
                ['ATFE','OK']]

        for c,r in cmds:
            self.sendAtCmd(c, r)

    def setAllowLongMessages(self, value):
        self.sendAtCmd('ATAL%i' % value)

    def setProtocol(self, prot):
        if prot == 'CAN_11_500':
            self.sendAtCmd('ATSP6','6 = ISO 15765-4, CAN (11/500)')
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setIDFilter(self, filter):
        self.sendAtCmd('ATCF' + str(filter))

    def setCANRxMask(self, mask):
        self.sendAtCmd('ATCM' + str(mask))

    def setCANRxFilter(self, addr):
        self.sendAtCmd('ATCRA' + str(addr))

