""" Module implementing an interface through Linux's socket CAN interface """
from time import sleep
from socket import (socket, timeout,
                    AF_CAN, PF_CAN, SOCK_DGRAM, SOCK_RAW, CAN_ISOTP,
                    CAN_RAW, CAN_EFF_FLAG, CAN_EFF_MASK, CAN_RAW_FILTER,
                    SOL_CAN_BASE, SOL_CAN_RAW)
from struct import pack, unpack
import logging
import sys
from pyroute2 import IPRoute
from . import NoData, CanError

if sys.version_info[0:2] <= (3, 7):
    raise NotImplementedError("SocketCAN requires at least python 3.7!")

SOL_CAN_ISOTP = SOL_CAN_BASE + CAN_ISOTP
CAN_ISOTP_OPTS = 1
CAN_ISOTP_RECV_FC = 2
CAN_ISOTP_TX_STMIN = 3
CAN_ISOTP_RX_STMIN = 4
CAN_ISOTP_LL_OPTS = 5
CAN_ISOTP_TX_PADDING = 0x4
CAN_ISOTP_RX_PADDING = 0x8
CAN_ISOTP_CHK_PAD_LEN = 0x10
CAN_ISOTP_CHK_PAD_DATA = 0x20

CANFMT = "<IB3x8s"


def can_str(msg):
    """ Returns a text representation of a CAN frame """
    can_id, length, data = unpack(CANFMT, msg)
    return "%x#%s (%d)" % (can_id & CAN_EFF_MASK, data.hex(' '), length)


class SocketCAN:
    """ Socket CAN interface """

    def __init__(self, config):
        self._log = logging.getLogger("EVNotiPi/SocketCAN")
        self._log.info("Initializing SocketCAN")

        self._config = config

        self._sock_can = None
        self._sock_isotp = None

        self._can_id = 0x7df
        self._can_filter = None
        self._can_mask = 0x7ff
        self._is_extended = False

        self.init_dongle()

    def init_dongle(self):
        """ Set up the network interface and initialize socket """
        ip_route = IPRoute()
        ifidx = ip_route.link_lookup(ifname=self._config['port'])[0]
        link = ip_route.link('get', index=ifidx)
        if 'state' in link[0] and link[0]['state'] == 'up':
            ip_route.link('set', index=ifidx, state='down')
            sleep(1)

        ip_route.link('set', index=ifidx, type='can',
                      txqlen=4000, bitrate=self._config['speed'])
        ip_route.link('set', index=ifidx, state='up')
        ip_route.close()

        if self._sock_can:
            self._sock_can.close()

        # test if kernel supports CAN_ISOTP
        try:
            sock = socket(AF_CAN, SOCK_DGRAM, CAN_ISOTP)
            sock.close()
            # CAN_ISOTP_TX_PADDING CAN_ISOTP_RX_PADDING CAN_ISOTP_CHK_PAD_LEN CAN_ISOTP_CHK_PAD_DATA
            opts = CAN_ISOTP_TX_PADDING | CAN_ISOTP_RX_PADDING | CAN_ISOTP_CHK_PAD_LEN
            # if self._is_extended:
            #    # CAN_ISOTP_EXTEND_ADDR
            #    opts |= 0x002
            self._sock_opt_isotp_opt = pack(
                "=LLBBBB", opts, 0, 0, 0xAA, 0xFF, 0)
            self._sock_opt_isotp_fc = pack("=BBB", 0, 0, 0)
            # select implementation of send_command_ex
            self.send_command_ex = self.send_command_ex_isotp
            self._log.info("using ISO-TP support")
        except OSError:
            # CAN_ISOTP not supported
            self.send_command_ex = self.send_command_ex_canraw

        self._sock_can = socket(PF_CAN, SOCK_RAW, CAN_RAW)
        try:
            self._sock_can.bind((self._config['port'],))
            self._sock_can.settimeout(0.2)
        except OSError:
            self._log.error("Could not bind to %s", self._config['port'])

    def send_command(self, cmd):
        """ Send a command and return the response """
        try:
            cmd_len = len(cmd)
            assert cmd_len < 8

            msg_data = (bytes([cmd_len]) + cmd).ljust(8, b'\x00')  # Pad cmd to 8 bytes

            can_id = self._can_id | CAN_EFF_FLAG if self._is_extended else self._can_id
            cmd_msg = pack(CANFMT, can_id, len(msg_data), msg_data)

            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("%s send message", can_str(cmd_msg))

            self._sock_can.send(cmd_msg)

            data = {}
            data_len = {}
            last_idx = {}

            while True:
                self._log.debug("waiting recv msg")
                msg = self._sock_can.recv(16)
                can_id, length, msg_data = unpack(CANFMT, msg)

                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug("Got %x %i %s", can_id, length, msg_data.hex(' '))

                can_id &= CAN_EFF_MASK
                msg_data = msg_data[:length]
                frame_type = msg_data[0] & 0xf0

                if frame_type == 0x00:
                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("%s single frame", can_str(msg))

                    data_len[can_id] = msg_data[0] & 0x0f
                    data[can_id] = bytes(msg_data[1:])
                    break

                elif frame_type == 0x10:
                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("%s first frame", can_str(msg))

                    data_len[can_id] = (msg_data[0] & 0x0f) + msg_data[1]
                    data[can_id] = bytearray(msg_data[2:])

                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("Send flow control message")

                    flow_msg = pack(CANFMT, can_id, 8, b'\x00\x00\x00\x00\x00\x00\x00')

                    self._sock_can.send(flow_msg)

                    last_idx[can_id] = 0

                elif frame_type == 0x20:
                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("%s consecutive frame", can_str(msg))

                    idx = msg_data[0] & 0x0f
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx(%d) idx(%d)" %
                                       (last_idx[can_id], idx))

                    frame_len = min(7, data_len[can_id] - len(data[can_id]))
                    data[can_id].extend(msg_data[1:frame_len+1])
                    last_idx[can_id] = idx

                    all_data_seen = True
                    for cid, dlen in data_len.items():
                        if dlen != len(data[cid]):
                            all_data_seen = False

                    if all_data_seen:
                        # All frames seen, exit loop
                        break

                elif frame_type == 0x30:
                    raise CanError(
                        "Unexpected flow control: %s" % (can_str(msg)))
                else:
                    raise CanError(
                        "Unexpected message: %s" % (can_str(msg)))

        except timeout as err:
            raise NoData("Command timed out %s: %s" % (cmd.hex(' '), err))
        except OSError as err:
            raise CanError("Failed Command %s: %s" % (cmd.hex(' '), err))

        if len(data) == 0:
            raise NoData('Empty data')

        return data

    def send_command_ex_isotp(self, cmd, cantx, canrx):
        """ Send a command using specified can tx id and
            return response from can rx id.
            Implemented using kernel level iso-tp. """
        try:
            with socket(AF_CAN, SOCK_DGRAM, CAN_ISOTP) as sock:
                sock.setsockopt(SOL_CAN_ISOTP, CAN_ISOTP_OPTS,
                                self._sock_opt_isotp_opt)
                sock.setsockopt(SOL_CAN_ISOTP, CAN_ISOTP_RECV_FC,
                                self._sock_opt_isotp_fc)

                sock.bind((self._config['port'], canrx, cantx))
                sock.settimeout(0.2)

                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug("canrx(%s) cantx(%s) cmd(%s)",
                                    hex(canrx), hex(cantx), cmd.hex(' '))
                sock.send(cmd)
                data = sock.recv(4096)
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug(data.hex(' '))
        except timeout as err:
            raise NoData("Command timed out {}: {}".format(cmd.hex(' '), err))
        except OSError as err:
            raise CanError("Failed Command {}: {}".format(cmd.hex(' '), err))

        if not data or len(data) == 0:
            raise NoData('NO DATA')

        return data

    def send_command_ex_canraw(self, cmd, cantx, canrx):
        """ Send a command using specified can tx id and
            return response from can rx id. """
        try:
            cmd_len = len(cmd)
            assert cmd_len < 8

            msg_data = (bytes([cmd_len]) + cmd).ljust(8, b'\x00')  # Pad cmd to 8 bytes

            if self._is_extended:
                cantx |= CAN_EFF_FLAG

            cmd_msg = pack(CANFMT, cantx, len(msg_data), msg_data)

            self.set_filters_ex([{
                'id':   canrx,
                'mask': 0x1fffffff if self._is_extended else 0x7ff
            }])

            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("%s send messsage", can_str(cmd_msg))

            self._sock_can.send(cmd_msg)

            data = None
            data_len = 0
            last_idx = 0

            while True:
                self._log.debug("waiting recv msg")
                msg = self._sock_can.recv(72)
                can_id, length, msg_data = unpack(CANFMT, msg)

                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug("Got %x %i %s", can_id, length, msg_data.hex(' '))

                can_id &= CAN_EFF_MASK
                msg_data = msg_data[:length]
                frame_type = msg_data[0] & 0xf0

                if frame_type == 0x00:
                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("%s single frame", can_str(msg))

                    data_len = msg_data[0] & 0x0f
                    data = bytes(msg_data[1:data_len+1])
                    break

                elif frame_type == 0x10:
                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("%s first frame", can_str(msg))

                    data_len = (msg_data[0] & 0x0f) + msg_data[1]
                    data = bytearray(msg_data[2:])

                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("Send flow control message")

                    flow_msg = pack(CANFMT, cantx, 8, b'\x00\x00\x00\x00\x00\x00\x00')

                    self._sock_can.send(flow_msg)

                    last_idx = 0

                elif frame_type == 0x20:
                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("%s consecutive frame", can_str(msg))

                    idx = msg_data[0] & 0x0f
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx(%d) idx(%d)" %
                                       (last_idx, idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(msg_data[1:frame_len+1])
                    last_idx = idx

                    if data_len == len(data):
                        # All frames seen, exit loop
                        break

                elif frame_type == 0x30:
                    raise CanError("Unexpected flow control: %s" % (can_str(msg)))
                else:
                    raise CanError("Unexpected message: %s" % (can_str(msg)))

        except timeout as err:
            raise NoData("Command timed out %s: %s" % (cmd.hex(' '), err))
        except OSError as err:
            raise CanError("Failed Command %s: %s" % (cmd.hex(' '), err))

        if not data or data_len == 0:
            raise NoData('NO DATA')
        if data_len != len(data):
            raise CanError("Data length mismatch %s: %d vs %d %s" %
                           (cmd.hex(' '), data_len, len(data), data.hex(' ')))

        return data

    def read_data_simple(self, timeout=None):
        """ Read a single frame. """
        try:
            data = {}

            self._sock_can.settimeout(timeout)
            msg = self._sock_can.recv(72)
            can_id, length, msg_data = unpack(CANFMT, msg)
            can_id &= CAN_EFF_MASK
            msg_data = msg_data[:length]

            data[can_id] = msg_data

        except timeout as err:
            raise CanError("Recv timed out: %s" % (err))
        except OSError as err:
            raise CanError("CAN read error: %s" % (err))

        if len(data) == 0:
            raise NoData(b'NO DATA')

        return data

    def set_protocol(self, prot):
        """ select the CAN falvour """
        if prot == 'CAN_11_500':
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self._is_extended = True
        else:
            raise Exception('Unsupported protocol %s' % prot)

        self.init_dongle()

    def set_can_id(self, can_id):
        """ Set the can tx id for send_command """
        assert isinstance(can_id, int)

        self._can_id = can_id

    def set_can_rx_mask(self, mask):
        """ Set can rx mask for send_command and read_data_simple """
        assert isinstance(mask, int)

        self._can_mask = mask

        self.set_filters_ex([{
            'id':   self._can_filter,
            'mask': self._can_mask,
        }])

    def set_can_rx_filter(self, addr):
        """ Set can rx filter for send_command and read_data_simple """
        assert isinstance(addr, int)

        self._can_filter = addr

        self.set_filters_ex([{
            'id':   self._can_filter,
            'mask': self._can_mask,
        }])

    def set_filters_ex(self, filters):
        """ Set filters on  the socket """
        filter_bin = bytearray()
        for flt in filters:
            filter_bin.extend(pack("=II", flt['id'], flt['mask']))

        self._sock_can.setsockopt(SOL_CAN_RAW, CAN_RAW_FILTER, filter_bin)
