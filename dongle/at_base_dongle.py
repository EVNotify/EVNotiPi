""" Implement base class for ELM327-ish serial donghles """
from threading import Lock
from time import sleep
import math
import logging
import serial
from . import NoData, CanError


class AtBase:
    """ Base class for ELM327 and similar """

    def __init__(self, dongle):
        self._log = logging.getLogger("EVNotiPi/%s" % __name__)
        self._log.info("Initializing OBD2 interface")

        self._serial_lock = Lock()
        self._serial = serial.Serial(dongle['port'],
                                     baudrate=dongle['speed'],
                                     timeout=1)
        self.init_dongle()

        self._config = dongle

        self._current_canid = 0
        self._current_canfilter = 0
        self._current_canmask = 0
        self._is_extended = False
        # These need to be redefined by the actual dongle module
        self._ret_no_data = None
        self._ret_can_error = None

    def init_dongle(self):
        """ Empty method, needs to be overriden"""
        raise NotImplementedError()

    def set_can_id(self, can_id):
        """ Empty method, needs to be overriden"""
        raise NotImplementedError()

    def set_can_rx_filter(self, can_id):
        """ Empty method, needs to be overriden"""
        raise NotImplementedError()

    def set_can_rx_mask(self, mask):
        """ Empty method, needs to be overriden"""
        raise NotImplementedError()

    def talk_to_dongle(self, cmd, expect=None):
        """ Send command to dongle and return the response as string. """
        try:
            with self._serial_lock:
                while self._serial.in_waiting:   # Clear the input buffer
                    self._log.warning("Stray data in buffer: %s",
                                      self._serial.read(self._serial.in_waiting))
                    sleep(0.1)

                self._log.debug("Send command: %s", cmd)
                self._serial.write(bytes(cmd + '\r\n', 'ascii'))
                ret = bytearray()
                while True:
                    if not self._serial.in_waiting:
                        sleep(0.1)
                        continue
                    data = self._serial.read(self._serial.in_waiting)

                    endidx = data.find(b'>')
                    if endidx >= 0:
                        ret.extend(data[:endidx])
                        break

                    ret.extend(data)

                self._log.debug("Received: %s", ret)

                if expect:
                    expect = bytes(expect, 'ascii')
                    if expect not in ret:
                        raise Exception("Expected %s, got %s" % (expect, ret))

        except serial.SerialTimeoutException:
            ret = b'TIMEOUT'

        return ret.strip(b'\r\n')

    def send_at_cmd(self, cmd, expect='OK'):
        """ Send AT command to dongle and return response. """
        ret = self.talk_to_dongle(cmd, expect)
        return ret.split(b"\r\n")[-1]

    def send_command(self, cmd):
        """ Convert bytearray "cmd" to string,
            send to dongle and parse the reponse. """
        cmd = cmd.hex()
        ret = self.talk_to_dongle(cmd)

        if ret in self._ret_no_data:
            raise NoData(ret)

        if ret in self._ret_can_error:
            raise CanError("Failed Command %s\n%s" % (cmd, ret))

        try:
            data = {}
            raw = ret.split(b'\r\n')
            lines = None

            for line in raw:
                if len(line) != 19:
                    raise ValueError

                identifier = int(line[0:3], 16)
                frame_type = int(line[3:4], 16)

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
                    idx = int(line[4:5], 16)
                else:                   # Unexpected frame
                    raise ValueError

                if identifier not in data:
                    data[identifier] = [None] * lines

                data[identifier][idx] = bytes.fromhex(str(line[5:], 'ascii'))

            # Check if all entries are filled
            for values in data.values():
                for value in values:
                    if value is None:
                        raise ValueError

        except ValueError:
            raise CanError("Failed Command %s\n%s" % (cmd, ret))

        return data

    def send_command_ex(self, cmd, cantx, canrx):
        """ Convert bytearray "cmd" to string,
            send to dongle and parse the reponse.
            Also handles filters and masks. """
        cmd = cmd.hex()
        self.set_can_id(cantx)
        self.set_can_rx_filter(canrx)
        self.set_can_rx_mask(0x1fffffff if self._is_extended else 0x7ff)

        ret = self.talk_to_dongle(cmd)

        if ret in self._ret_no_data:
            raise NoData(ret)

        if ret in self._ret_can_error:
            raise CanError("Failed Command %s\n%s" % (cmd, ret))

        try:
            data = None
            data_len = 0
            last_idx = 0
            raw = str(ret, 'ascii').split('\r\n')

            for line in raw:
                if ((self._is_extended is False and len(line) != 19)
                        or (self._is_extended is True and len(line) != 27)):
                    raise ValueError

                offset = 8 if self._is_extended else 3

                frame_type = int(line[offset:offset+1], 16)

                if frame_type == 0:     # Single frame
                    self._log.debug("%s single frame", line)
                    data_len = int(line[offset+1:offset+2], 16)
                    data = bytes.fromhex(line[offset+2:data_len*2+offset+2])
                    break

                elif frame_type == 1:   # First frame
                    self._log.debug("%s first frame", line)
                    data_len = int(line[offset+1:offset+4], 16)
                    data = bytearray.fromhex(line[offset+4:])
                    last_idx = 0

                elif frame_type == 2:   # Consecutive frame
                    self._log.debug("%s consecutive frame", line)
                    idx = int(line[offset+1:offset+2], 16)
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx(%d) idx(%d)" %
                                       (last_idx, idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(bytearray.fromhex(
                        line[offset+2:frame_len*2+offset+2]))
                    last_idx = idx

                    if data_len == len(data):
                        break

                else:                   # Unexpected frame
                    raise ValueError

            if not data or data_len == 0:
                raise NoData('NO DATA')

            if data_len != len(data):
                raise CanError("Data length mismatch %s: %d vs %d %s" %
                               (cmd, data_len, len(data), data.hex()))

        except ValueError:
            raise CanError("Failed Command %s\n%s" % (cmd, ret))

        return data
