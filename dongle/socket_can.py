""" Module implementing an interface through Linux's socket CAN interface """
from time import sleep
from socket import (socket, timeout as sock_timeout,
                    AF_CAN, PF_CAN, SOCK_DGRAM, SOCK_RAW, CAN_ISOTP,
                    CAN_RAW, CAN_EFF_FLAG, CAN_EFF_MASK, CAN_RAW_FILTER,
                    SOL_CAN_BASE, SOL_CAN_RAW)
from struct import Struct, pack
import logging
import sys
from pyroute2 import IPRoute
from . import NoData, CanError

if sys.version_info[0:2] < (3, 7):
    raise NotImplementedError("SocketCAN requires at least python 3.7!")

if sys.version_info[0:2] == (3, 7):
    # Fix bug in python 3.7's socket module
    SOL_CAN_BASE = 0x64
    SOL_CAN_RAW = 0x65

SOL_CAN_ISOTP = SOL_CAN_BASE + CAN_ISOTP
CAN_ISOTP_OPTS = 1
CAN_ISOTP_RECV_FC = 2
CAN_ISOTP_TX_STMIN = 3
CAN_ISOTP_RX_STMIN = 4
CAN_ISOTP_LL_OPTS = 5
CAN_ISOTP_EXTEND_ADDR = 0x2
CAN_ISOTP_TX_PADDING = 0x4
CAN_ISOTP_RX_PADDING = 0x8
CAN_ISOTP_CHK_PAD_LEN = 0x10
CAN_ISOTP_CHK_PAD_DATA = 0x20

CANFMT = Struct("<IB3x8s")


def can_str(msg):
    """ Returns a text representation of a CAN frame """
    can_id, length, data = CANFMT.unpack(msg)
    return "%x#%s (%d)" % (can_id & CAN_EFF_MASK, data.hex(), length)


class CanSocket(socket):
    """ Extend socket class with some helper functions """

    def __init__(self, family=-1, type=-1, proto=-1, fileno=None):
        socket.__init__(self, family, type, proto, fileno)
        self._can_id = None
        self._can_mask = None
        self._can_filter = None

    def set_can_id(self, can_id):
        """ Set the con id for transmission """
        if not isinstance(can_id, int):
            raise ValueError

        self._can_id = can_id

    def set_can_rx_mask(self, mask):
        """ Set the can receive mask """
        if not isinstance(mask, int):
            raise ValueError

        self._can_mask = mask

        if self._can_filter is not None:
            self.set_filters_ex([{
                'id':   self._can_filter,
                'mask': self._can_mask,
            }])

    def set_can_rx_filter(self, addr):
        """ Set the can receive filter """
        if not isinstance(addr, int):
            raise ValueError

        self._can_filter = addr

        if self._can_mask is not None:
            self.set_filters_ex([{
                'id':   self._can_filter,
                'mask': self._can_mask,
            }])

    def set_filters_ex(self, filters):
        """ Set filters on the socket """
        bin_filter = bytearray()
        for flt in filters:
            bin_filter.extend(pack("=II", flt['id'], flt['mask']))

        self.setsockopt(SOL_CAN_RAW, CAN_RAW_FILTER, bin_filter)


class SocketCan:
    """ Socket CAN interface """

    def __init__(self, config):
        self._log = logging.getLogger("EVNotiPi/SocketCAN")
        self._log.info("Initializing SocketCAN")

        self._config = config

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

        # test if kernel supports CAN_ISOTP
        try:
            sock = CanSocket(AF_CAN, SOCK_DGRAM, CAN_ISOTP)
            sock.close()
            # CAN_ISOTP_TX_PADDING CAN_ISOTP_RX_PADDING CAN_ISOTP_CHK_PAD_LEN CAN_ISOTP_CHK_PAD_DATA
            opts = CAN_ISOTP_TX_PADDING | CAN_ISOTP_RX_PADDING | CAN_ISOTP_CHK_PAD_LEN
            # if self._is_extended:
            #    opts |= CAN_ISOTP_EXTEND_ADDR
            self._sock_opt_isotp_opt = pack("=LLBBBB", opts, 0, 0, 0xAA, 0xFF, 0)
            self._sock_opt_isotp_fc = pack("=BBB", 0, 0, 0)
            # select implementation of send_command_ex
            self.send_command_ex = self.send_command_ex_isotp
            self._log.info("using ISO-TP support")
        except OSError as err:
            if err.errno == 93:
                # CAN_ISOTP not supported
                self.send_command_ex = self.send_command_ex_canraw
            else:
                raise

        self._can_raw_sock = CanSocket(PF_CAN, SOCK_RAW, CAN_RAW)
        self._can_raw_sock.bind((self._config['port'],))

    def send_command_ex_isotp(self, cmd, cantx, canrx):
        """ Send a command using specified can tx id and
            return response from can rx id.
            Implemented using kernel level iso-tp. """
        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug("sendCommandEx_ISOTP cmd(%s) cantx(%x) canrx(%x)",
                            cmd.hex(), canrx, cantx)

        if self._is_extended:
            cantx |= CAN_EFF_FLAG
            canrx |= CAN_EFF_FLAG

        try:
            with CanSocket(AF_CAN, SOCK_DGRAM, CAN_ISOTP) as sock:
                sock.setsockopt(SOL_CAN_ISOTP, CAN_ISOTP_OPTS,
                                self._sock_opt_isotp_opt)
                sock.setsockopt(SOL_CAN_ISOTP, CAN_ISOTP_RECV_FC,
                                self._sock_opt_isotp_fc)

                sock.bind((self._config['port'], canrx, cantx))
                sock.settimeout(0.2)

                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug("canrx(%s) cantx(%s) cmd(%s)",
                                    hex(canrx), hex(cantx), cmd.hex())
                sock.send(cmd)
                data = sock.recv(4096)
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug(data.hex())
        except sock_timeout as err:
            raise NoData("Command timed out %s: %s" % (cmd.hex(), err))
        except OSError as err:
            raise CanError("Failed Command %s: %s" % (cmd.hex(), err))

        if not data or len(data) == 0:
            raise NoData('NO DATA')

        return data

    def send_command_ex_canraw(self, cmd, cantx, canrx):
        """ Send a command using specified can tx id and
            return response from can rx id. """
        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug("sendCommandEx_CANRAW cmd(%s) cantx(%x) canrx(%x)",
                            cmd.hex(), canrx, cantx)

        if self._is_extended:
            cantx |= CAN_EFF_FLAG
            canrx |= CAN_EFF_FLAG

        try:
            cmd_len = len(cmd)
            assert cmd_len < 8

            msg_data = (bytes([cmd_len]) + cmd).ljust(8, b'\x00')  # Pad cmd to 8 bytes

            cmd_msg = CANFMT.pack(cantx, len(msg_data), msg_data)

            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("%s send messsage", can_str(cmd_msg))

            with CanSocket(PF_CAN, SOCK_RAW, CAN_RAW) as sock:
                sock.bind((self._config['port'],))
                sock.settimeout(0.2)

                sock.setFiltersEx([{
                    'id':   canrx,
                    'mask': 0x1fffffff if self._is_extended else 0x7ff
                    }])

                sock.send(cmd_msg)

                data = None
                data_len = 0
                last_idx = 0

                while True:
                    self._log.debug("waiting recv msg")
                    msg = sock.recv(72)
                    can_id, length, msg_data = CANFMT.unpack(msg)

                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("Got %x %i %s", can_id,
                                        length, msg_data.hex())

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

                        flow_msg = CANFMT.pack(cantx, 8, b'\x00\x00\x00\x00\x00\x00\x00')

                        sock.send(flow_msg)

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

        except sock_timeout as err:
            raise NoData("Command timed out %s: %s" % (cmd.hex(), err))
        except OSError as err:
            raise CanError("Failed Command %s: %s" % (cmd.hex(), err))

        if not data or data_len == 0:
            raise NoData('NO DATA')
        if data_len != len(data):
            raise CanError("Data length mismatch %s: %d vs %d %s" %
                           (cmd.hex(), data_len, len(data), data.hex()))

        return data

    def read_raw_frame(self, timeout=None):
        """ Read a single frame. """
        try:
            self._can_raw_sock.settimeout(timeout)

            msg = self._can_raw_sock.recv(72)

            can_id, length, msg_data = CANFMT.unpack(msg)
            can_id &= CAN_EFF_MASK

            if len(msg_data) == 0:
                raise NoData(b'NO DATA')

            data = {
                'can_id': can_id,
                'data_len': length,
                'data': msg_data[:length]
                }

            return data

        except sock_timeout as err:
            raise CanError("Recv timed out: %s" % (err))
        except OSError as err:
            raise CanError("CAN read error: %s" % (err))

    def set_raw_mask(self, mask):
        """ Set the can receive mask of the raw socket"""
        self._can_raw_sock.set_can_rx_mask(mask)

    def set_raw_filter(self, addr):
        """ Set the can receive filter of the raw socket """
        self._can_raw_sock.set_can_rx_filter(addr)

    def set_raw_filters_es(self, filters):
        """ Set filters on the socket of the raw socket """
        self._can_raw_sock.set_filters_ex(filters)

    def set_protocol(self, prot):
        """ select the CAN flavor """
        if prot == 'CAN_11_500':
            self._is_extended = False
        elif prot == 'CAN_29_500':
            self._is_extended = True
        else:
            raise ValueError('Unsupported protocol %s' % prot)

        self.init_dongle()
