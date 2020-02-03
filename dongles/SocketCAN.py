from dongle import *
import socket
import struct
import math
from pyroute2 import IPRoute
from time import sleep
import logging

CANFMT = "<IB3x8s"

def canStr(msg):
    can_id, length, data = struct.unpack(CANFMT, msg)
    return "{:x}#{} ({})".format(can_id & socket.CAN_EFF_MASK, data.hex(), length)

class SocketCAN:
    def __init__(self, config, watchdog = None):
        self.log = logging.getLogger("EVNotiPi/SocketCAN")
        self.log.info("Initializing SocketCAN")

        self.config = config

        self.watchdog = watchdog
        if not watchdog:
            GPIO.setmode(GPIO.BCM)
            self.pin = dongle['shutdown_pin']
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=dongle['pup_down'])

        self.socket = None
        self.initDongle()

        self.can_id = 0x7df
        self.can_filter = None
        self.can_mask = 0x7ff
        self.is_extended = False

    def sendCommand(self, cmd):
        try:
            cmd_len = len(cmd)
            assert(cmd_len < 8)

            msg_data = (bytes([cmd_len]) + cmd).ljust(8, b'\x00') # Pad cmd to 8 bytes

            cmd_msg = struct.pack(CANFMT, self.can_id | socket.CAN_EFF_FLAG if self.is_extended else self.can_id,
                    len(msg_data), msg_data)

            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug("%s send message", canStr(can_msg))

            self.socket.send(cmd_msg)

            data = {}
            data_len = {}

            while True:
                msg = self.socket.recv(16)
                can_id, length, msg_data = struct.unpack(CANFMT, msg)
                can_id &= socket.CAN_EFF_MASK
                msg_data = msg_data[:length]
                frame_type = msg_data[0] & 0xf0

                if frame_type == 0x00:
                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("%s single frame", canStr(msg))

                    data_len[can_id] = msg_data[0] & 0x0f
                    data[can_id] = [bytes(msg_data[1:])]
                    break

                elif frame_type == 0x10:
                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("%s first frame", canStr(msg))

                    data_len[can_id] = (msg_data[0] & 0x0f) + msg_data[1]
                    lines = math.ceil(data_len[can_id] / 7)
                    data[can_id] = [None] * lines
                    data[can_id][0] = bytes(msg_data[2:])

                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("Send flow control message")

                    flow_msg = struct.pack(CANFMT, self.can_id | socket.CAN_EFF_FLAG if self.is_extended else self.can_id,
                            8, b'0\x00\x00\x00\x00\x00\x00\x00')

                    self.socket.send(flow_msg)

                elif frame_type == 0x20:
                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("%s consecutive frame", canStr(msg))

                    idx = msg_data[0] & 0x0f
                    data[can_id][idx] = bytes(msg_data[1:])
                    if idx + 1 == data_len[can_id]:
                        # All frames seen, exit loop
                        break

                elif frame_type == 0x30:
                    raise CanError("Unexpected flow control: {}".format(canStr(msg)))
                else:
                    raise CanError("Unexpected message: {}".format(canStr(msg)))

        except socket.timeout as e:
            raise NoData("Command timed out {}: {}".format(cmd.hex(), e))
        except OSError as e:
            raise CanError("Failed Command {}: {}".format(cmd.hex(), e))

        if len(data) == 0:
            raise NoData(b'NO DATA')

        try:
            # Check if all entries are filled
            for key, val in data.items():
                for i in val:
                    if i == None:
                        raise ValueError

        except ValueError:
            raise CanError("Failed Command {}: {}".format(cmd.hex(), data))

        return data

    def sendCommandEx(self, cmd, cantx, canrx):
        try:
            cmd_len = len(cmd)
            assert(cmd_len < 8)

            msg_data = (bytes([cmd_len]) + cmd).ljust(8, b'\x00') # Pad cmd to 8 bytes

            cmd_msg = struct.pack(CANFMT, cantx | socket.CAN_EFF_FLAG if self.is_extended else cantx,
                    len(msg_data), msg_data)

            self.setFiltersEx([{
                'id':   canrx,
                'mask': 0x1fffffff if self.is_extended else 0x7ff
                }])

            if self.log.isEnabledFor(logging.DEBUG):
                self.log.debug("%s send messsage", canStr(cmd_msg))

            self.socket.send(cmd_msg)

            data = None
            data_len = 0
            last_idx = 0

            while True:
                self.log.debug("waiting recv msg")
                msg = self.socket.recv(72)
                can_id, length, msg_data = struct.unpack(CANFMT, msg)
                self.log.debug("Got %x %i %s",can_id, length, msg_data.hex())
                can_id &= socket.CAN_EFF_MASK
                msg_data = msg_data[:length]
                frame_type = msg_data[0] & 0xf0

                if frame_type == 0x00:
                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("%s single frame", canStr(msg))

                    data_len = msg_data[0] & 0x0f
                    data = bytes(msg_data[1:data_len+1])
                    break

                elif frame_type == 0x10:
                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("%s first frame", canStr(msg))

                    data_len = (msg_data[0] & 0x0f) + msg_data[1]
                    data = bytearray(msg_data[2:])

                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("Send flow control message")

                    flow_msg = struct.pack(CANFMT, cantx | socket.CAN_EFF_FLAG if self.is_extended else cantx,
                            8, b'0\x00\x00\x00\x00\x00\x00\x00')

                    self.socket.send(flow_msg)

                    last_idx = 0

                elif frame_type == 0x20:
                    if self.log.isEnabledFor(logging.DEBUG):
                        self.log.debug("%s consecutive frame", canStr(msg))

                    idx = msg_data[0] & 0x0f
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx({}) idx({})".format(last_idx,idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(msg_data[1:frame_len+1])
                    last_idx = idx

                    if data_len == len(data):
                        # All frames seen, exit loop
                        break

                elif frame_type == 0x30:
                    raise CanError("Unexpected flow control: {}".format(canStr(msg)))
                else:
                    raise CanError("Unexpected message: {}".format(canStr(msg)))

        except socket.timeout as e:
            raise NoData("Command timed out {}: {}".format(cmd.hex(), e))
        except OSError as e:
            raise CanError("Failed Command {}: {}".format(cmd.hex(), e))

        if not data or data_len == 0:
            raise NoData('NO DATA')
        if data_len != len(data):
            raise CanError("Data length mismatch {}: {} vs {} {}".format(cmd.hex(), data_len, len(data), data.hex()))

        return data

    def readDataSimple(self, timeout=None):
        try:
            data = {}

            msg = self.socket.recv(72)
            can_id, length, msg_data = struct.unpack(CANFMT, msg)
            can_id &= socket.CAN_EFF_MASK
            msg_data = msg_data[:length]

            data[can_id] = msg_data

        except socket.timeout as e:
            raise CanError("Recv timed out: {}".format(e))
        except OSError as e:
            raise CanError("CAN read error: {}".format(e))


        if len(data) == 0:
            raise NoData(b'NO DATA')

        return data

    def initDongle(self):
        ip = IPRoute()
        ifidx = ip.link_lookup(ifname=self.config['port'])[0]
        link = ip.link('get',index=ifidx)
        if 'state' in link[0] and link[0]['state'] == 'up':
            ip.link('set', index=ifidx, state='down')
            sleep(1)

        ip.link('set', index=ifidx, type='can', txqlen=1, bitrate=self.config['speed'])
        ip.link('set', index=ifidx, state='up')
        ip.close()

        if self.socket:
            self.socket.close()

        self.socket = socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        try:
            self.socket.bind((self.config['port'],))
            self.socket.settimeout(0.2)
        except OSError:
            self.log.error("Could not bind to %i", self.config['port'])


    def setProtocol(self, prot):
        # SocketCAN doesn't support anything else
        if prot == 'CAN_11_500':
            self.is_extended = False
        elif prot == 'CAN_29_500':
            self.is_extended = True
        else:
            raise Exception('Unsupported protocol %s' % prot)

    def setCanID(self, can_id):
        if not isinstance(can_id, int):
            raise ValueError

        self.can_id = can_id

    def setCANRxMask(self, mask):
        if not isinstance(mask, int):
            raise ValueError

        self.can_mask = mask

        self.setFiltersEx([{
            'id':   self.can_filter,
            'mask': self.can_mask,
            }])

    def setCANRxFilter(self, addr):
        if not isinstance(addr, int):
            raise ValueError

        self.can_filter = addr

        self.setFiltersEx([{
            'id':   self.can_filter,
            'mask': self.can_mask,
            }])

    def setFiltersEx(self, filters):
        flt = bytearray()
        for f in filters:
            flt.extend(struct.pack("=II",
                    f['id'],# | socket.CAN_EFF_FLAG if self.is_extended else f['id'],
                    f['mask']))

        self.socket.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER, flt)

    def getObdVoltage(self):
        if self.watchdog:
            return round(self.watchdog.getVoltage(), 2)

    def calibrateObdVoltage(self, realVoltage):
        if self.watchdog:
            self.watchdog.calibrateVoltage(realVoltage)

    def isCarAvailable(self):
        if self.watchdog:
            return self.watchdog.getShutdownFlag() == 0
        else
            return GPIO.input(self.pin) == False

