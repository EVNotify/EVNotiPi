from AtBaseDongle import *

class PiOBD2Hat(ATBASE):
    def __init__(self, dongle):
        ATBASE.__init__(self, dongle)
        self.ret_NoData = (b'NO DATA', b'TIMEOUT', b'CAN NO ACK')
        self.ret_CanError = (b'INPUT TIMEOUT', b'NO INPUT CHAR', b'UNKNOWN COMMAND',
                b'WRONG HEXCHAR COUNT', b'ILLEGAL COMMAND', b'SYNTAX ERROR',
                b'WRONG VALUE/RANGE', b'UNABLE TO CONNECT', b'BUS BUSY',
                b'NO FEEDBACK', b'NO SYNCBYTE', b'NO KEYBYTE',
                b'NO ADDRESSBYTE', b'WRONG PROTOCOL', b'DATA ERROR',
                b'CHECKSUM ERROR', b'NO ANSWER', b'COLLISION DETECT',
                b'CAN NO ANSWER', b'PRTOTOCOL 8 OR 9 REQUIRED',
                b'CAN ERROR')
        self.voltage_multiplier = 0.694

    def initDongle(self):
        cmds = (('ATRST','DIAMEX PI-OBD'),  # Cold start
                ('ATE0','OK'),              # Disable echo
                ('ATL1','OK'),              # Use \r\n
                ('ATOHS0','OK'),            # Disable space between HEX bytes
                ('ATH1','OK'),              # Display header
                ('ATST64','OK'))            # Input timeout (10 sec)

        for c,r in cmds:
            self.sendAtCmd(c, r)

    def setProtocol(self, prot):
        if prot == 'CAN_11_500':
            self.sendAtCmd('ATP6','6 = ISO 15765-4, CAN (11/500)')
            self.sendAtCmd('ATONI1')   # No init sequence
            self.is_extended = False
        elif prot == 'CAN_29_500':
            self.sendAtCmd('ATP7','7 = ISO 15765-4, CAN (29/500)')
            self.sendAtCmd('ATONI1')   # No init sequence
            self.is_extended = True
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setCanID(self, can_id):
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self.is_extended else '03X')

        if self.current_canid != can_id:
            self.sendAtCmd('ATCT' + can_id)
            self.current_canid = can_id

    def setCANRxMask(self, mask):
        if isinstance(mask, bytes):
            mask = str(mask)
        elif isinstance(mask, int):
            mask = format(mask, '08X' if self.is_extended else '03X')

        if self.current_canmask != mask:
            self.sendAtCmd('ATCM' + mask)
            self.current_canmask = mask

    def setCANRxFilter(self, addr):
        if isinstance(addr, bytes):
            addr = str(addr)
        elif isinstance(addr, int):
            addr = format(addr, '08X' if self.is_extended else '03X')

        if self.current_canfilter != addr:
            self.sendAtCmd('ATCR' + addr)
            self.current_canfilter = addr

    def getObdVoltage(self):
        ret = self.sendAtCmd('AT!10','V')
        return round(float(ret[:-1]) * self.voltage_multiplier, 2)

    def calibrateObdVoltage(self, realVoltage):
        ret = self.sendAtCmd('AT!10','V')
        self.voltage_multiplier = realVoltage / float(ret[:-1])
