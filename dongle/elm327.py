""" Module for ELM327 based dongles """
from .at_base_dongle import AtBase


class Elm327(AtBase):
    """ Implementation for ELM327 """

    def __init__(self, dongle):
        AtBase.__init__(self, dongle)
        self._ret_no_data = (b'NO DATA', b'DATA ERROR', b'ACT ALERT')
        self._ret_can_error = (b'BUFFER FULL', B'BUS BUSY', b'BUS ERROR', b'CAN ERROR',
                               b'ERR', b'FB ERROR', b'LP ALERT', b'LV RESET', b'STOPPED',
                               b'UNABLE TO CONNECT')

    def init_dongle(self):
        """ Send some initializing commands to the dongle. """
        cmds = (('ATZ', 'ELM327'),
                ('ATE0', 'OK'),
                ('ATL1', 'OK'),
                ('ATS0', 'OK'),
                ('ATH1', 'OK'),
                ('ATSTFF', 'OK'),
                ('ATFE', 'OK'))

        for cmd, exp in cmds:
            self.send_at_cmd(cmd, exp)

    def set_protocol(self, prot):
        """ Set the variant of CAN protocol """
        if prot == 'CAN_11_500':
            self.send_at_cmd('ATSP6', 'OK')
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self.send_at_cmd('ATSP7', 'OK')
            self._is_extended = True
        else:
            raise ValueError('Unsupported protocol %s' % prot)

    def set_can_id(self, can_id):
        """ Set CAN id to use for sent frames """
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self._is_extended else '03X')

        if self._current_canid != can_id:
            self.send_at_cmd('ATSH' + can_id)
            self._current_canid = can_id

    def set_can_rx_mask(self, mask):
        """ Set the CAN id mask for receiving frames """
        if isinstance(mask, bytes):
            mask = str(mask)
        elif isinstance(mask, int):
            mask = format(mask, '08X' if self._is_extended else '03X')

        if self._current_canmask != mask:
            self.send_at_cmd('ATCM' + mask)
            self._current_canmask = mask

    def set_can_rx_filter(self, can_id):
        """ Set the CAN id filter for receiving frames """
        if isinstance(can_id, bytes):
            can_id = str(can_id)
        elif isinstance(can_id, int):
            can_id = format(can_id, '08X' if self._is_extended else '03X')

        if self._current_canfilter != can_id:
            self.send_at_cmd('ATCF' + can_id)
            self._current_canfilter = can_id

    def get_obd_voltage(self):
        """ Get the voltage at the OBD port """
        ret = self.send_at_cmd('ATRV', None)
        return round(float(ret[:-1]), 2)

    def calibrate_obd_voltage(self, real_voltage):
        """ Calibrate the voltage sensor using an
            externally measured voltage reading """
        # CV dddd Calibrate the Voltage to dd.dd volts
        self.send_at_cmd('ATCV%04.0f' % (real_voltage * 100))
