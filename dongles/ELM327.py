from AtBaseDongle import *

class ELM327(ATBASE):
    def __init__(self, dongle, watchdog = None):
        ATBASE.__init__(self, dongle, watchdog)
        self.ret_NoData = (b'NO DATA', b'DATA ERROR', b'ACT ALERT')
        self.ret_CanError = (b'BUFFER FULL', B'BUS BUSY', b'BUS ERROR', b'CAN ERROR',
                b'ERR', b'FB ERROR', b'LP ALERT', b'LV RESET', b'STOPPED',
                b'UNABLE TO CONNECT')

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

    def setProtocol(self, prot):
        if prot == 'CAN_11_500':
            self.sendAtCmd('ATSP6','OK')
            self.is_extended = False
        elif prot == 'CAN_29_500':
            self.sendAtCmd('ATSP7','OK')
            self.is_extended = True
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setCanID(self, can_id):
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self.is_extended else '03X')

        if self.current_canid != can_id:
            self.sendAtCmd('ATSH' + can_id)
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
            self.sendAtCmd('ATCF' + addr)
            self.current_canfilter = addr

    def getObdVoltage(self):
        if self.watchdog:
            return round(self.watchdog.getVoltage(), 2)
        else:
            ret = self.sendAtCmd('ATRV')
            return round(float(ret[:-1]), 2)

    def calibrateObdVoltage(self, realVoltage):
        if self.watchdog:
            self.watchdog.calibrateVoltage(realVoltage)
        else:
            self.sendAtCmd('ATCV{:04.0f}'.format(realVoltage)) # CV dddd Calibrate the Voltage to dd.dd volts

