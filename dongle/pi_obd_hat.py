""" Module for Diamex Pi-OBD-Hat """
from .at_base_dongle import AtBase


class PiObd2Hat(AtBase):
    """ Implementation for Pi-OBD-Hat """

    def __init__(self, dongle):
        AtBase.__init__(self, dongle)
        self._ret_no_data = (b'NO DATA', b'TIMEOUT', b'CAN NO ACK')
        self._ret_can_error = (b'INPUT TIMEOUT', b'NO INPUT CHAR', b'UNKNOWN COMMAND',
                               b'WRONG HEXCHAR COUNT', b'ILLEGAL COMMAND', b'SYNTAX ERROR',
                               b'WRONG VALUE/RANGE', b'UNABLE TO CONNECT', b'BUS BUSY',
                               b'NO FEEDBACK', b'NO SYNCBYTE', b'NO KEYBYTE',
                               b'NO ADDRESSBYTE', b'WRONG PROTOCOL', b'DATA ERROR',
                               b'CHECKSUM ERROR', b'NO ANSWER', b'COLLISION DETECT',
                               b'CAN NO ANSWER', b'PRTOTOCOL 8 OR 9 REQUIRED',
                               b'CAN ERROR')
        self._voltage_multiplier = 0.694

    def init_dongle(self):
        """ Send some initializing commands to the dongle. """
        cmds = (('ATRST', 'DIAMEX PI-OBD'),  # Cold start
                ('ATE0', 'OK'),              # Disable echo
                ('ATL1', 'OK'),              # Use \r\n
                ('ATOHS0', 'OK'),            # Disable space between HEX bytes
                ('ATH1', 'OK'),              # Display header
                ('ATST64', 'OK'))            # Input timeout (10 sec)

        for cmd, exp in cmds:
            self.send_at_cmd(cmd, exp)

    def set_protocol(self, prot):
        """ Set the variant of CAN protocol """
        if prot == 'CAN_11_500':
            self.send_at_cmd('ATP6', '6 = ISO 15765-4, CAN (11/500)')
            self.send_at_cmd('ATONI1')   # No init sequence
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self.send_at_cmd('ATP7', '7 = ISO 15765-4, CAN (29/500)')
            self.send_at_cmd('ATONI1')   # No init sequence
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
            self.send_at_cmd('ATCT' + can_id)
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
            self.send_at_cmd('ATCR' + can_id)
            self._current_canfilter = can_id

    def get_obd_voltage(self):
        """ Get the voltage at the OBD port """
        ret = self.send_at_cmd('AT!10', 'V')
        return round(float(ret[:-1]) * self._voltage_multiplier, 2)

    def calibrate_obd_voltage(self, real_voltage):
        """ Calibrate the voltage sensor using an
            externally measured voltage reading """
        ret = self.send_at_cmd('AT!10', 'V')
        self._voltage_multiplier = real_voltage / float(ret[:-1])