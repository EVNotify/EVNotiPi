from serial import Serial
import logging
from pexpect import fdpexpect
from binascii import hexlify

class ELM327:

    class CAN_ERROR(Exception): pass
    class NO_DATA(Exception): pass

    def __init__(self, dongle):
        print("Init Dongle")
        self.serial = Serial(dongle['port'], baudrate=dongle['speed'], timeout=5)
        self.exp = fdpexpect.fdspawn(self.serial.fd)
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

        expect = bytes(expect, 'utf-8')
        cmd = bytes(cmd, 'utf-8')

    def sendCommand(self, cmd):
        """
        @cmd: should be hex-encoded
        """

        cmd = hexlify(cmd)
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

        if ret in [b'NO DATA', b'DATA ERROR', b'ACT ALERT']:
            raise ELM327.NO_DATA(ret)
        elif ret in [b'BUFFER FULL', B'BUS BUSY', b'BUS ERROR', b'CAN ERROR',
                b'ERR', b'FB ERROR', b'LP ALERT', b'LV RESET', b'STOPPED',
                b'UNABLE TO CONNECT']:
            raise ELM327.CAN_ERROR("Failed Command {}\n{}".format(cmd,ret))

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
            raise ELM327.CAN_ERROR("Failed Command {}\n{}".format(cmd,ret))

        return data

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

    def setCanID(self, can_id):
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, 'X')

        self.sendAtCmd('ATTA' + can_id)

    def setIDFilter(self, id_filter):
        if isinstance(id_filter, bytes):
            id_filter = str(id_filter)
        elif isinstance(id_filter, int):
            id_filter = format(id_filter, 'X')

        self.sendAtCmd('ATCF' + id_filter)

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

        self.sendAtCmd('ATCRA' + addr)

    def getObdVoltage(self):
        return None

