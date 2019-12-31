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

        if 'input_pin' in config:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.config['input_pin'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self.watchdog = watchdog

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

            msg_data = bytes([cmd_len]) + cmd + b"\00" * (7 - cmd_len) # Pad cmd to 8 bytes

            cmd_msg = struct.pack(CANFMT, self.can_id | socket.CAN_EFF_FLAG if self.is_extended else 0,
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

                    flow_msg = struct.pack(CANFMT, self.can_id | socket.CAN_EFF_FLAG if self.is_extended else 0,
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
            raise CanError("Command timed out {}: {}".format(cmd.hex(), e))
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

            msg_data = bytes([cmd_len]) + cmd + b"\00" * (7 - cmd_len) # Pad cmd to 8 bytes

            cmd_msg = struct.pack(CANFMT, cantx,
                    #| socket.CAN_EFF_FLAG if self.is_extended else 0,
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

                    flow_msg = struct.pack(CANFMT, cantx,
                            #| socket.CAN_EFF_FLAG if self.is_extended else 0,
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
            raise CanError("Command timed out {}: {}".format(cmd.hex(), e))
        except OSError as e:
            raise CanError("Failed Command {}: {}".format(cmd.hex(), e))

        if not data or data_len == 0:
            raise NoData('NO DATA')
        if data_len != len(data):
            raise CanError("Data length mismatch {}: {} vs {} {}".format(cmd.hex(), data_len, len(data), data.hex()))

        return data

    def sendCommandEx(self, cmd, cantx, canrx):
        try:
            cmd_len = len(cmd)
            assert(cmd_len < 8)

            msg_data = bytearray([cmd_len]) + cmd + b"\00" * (7 - cmd_len) # Pad cmd to 8 bytes

            is_extended = True if cantx > 0xfff else False

            self.cmd_msg = can.Message(extended_id = is_extended, arbitration_id = cantx, data = msg_data)

            self.bus.set_filters([{
                'can_id':   canrx,
                'can_mask': 0x1fffff if is_extended else 0x7ff
                }])

            #print(hexlify(cmd),msg_data)
            self.log.debug("{} Sent messsage".format(self.cmd_msg))
            self.bus.send(self.cmd_msg)

            data = b''
            data_len = 0

            while True:
                msg = self.bus.recv(1)
                self.log.debug(msg)

                if msg == None:
                    break

                if msg.data[0] & 0xf0 == 0x00:
                    self.log.debug("{} single frame".format(msg))
                    data_len = msg.data[0] & 0x0f
                    data = bytes(msg.data[1:(data_len+1)])

                elif msg.data[0] & 0xf0 == 0x10:
                    self.log.debug("{} first frame".format(msg))
                    data_len = (msg.data[0] & 0x0f) + msg.data[1]
                    data = bytes(msg.data[2:])

                    self.log.debug("Send flow control message")
                    flow_msg = can.Message(extended_id = is_extended, arbitration_id = cantx, data = [0x30,0,0,0,0,0,0,0])
                    self.bus.send(flow_msg)

                elif msg.data[0] & 0xf0 == 0x20:
                    self.log.debug("{} consecutive frame".format(msg))
                    idx = msg.data[0] & 0x0f
                    frame_len = min(7, data_len - len(data))
                    data += bytes(msg.data[1:frame_len])

                    if data_len == len(data):
                        break

                elif msg.data[0] & 0xf0 == 0x30:
                    raise CanError("Unexpected flow control: {}".format(msg))
                else:
                    raise CanError("Unexpected message: {}".format(msg))

        except OSError as e:
            raise CanError("Failed Command {}: {}".format(hexlify(cmd), e))

        if data_len != len(data):
            raise CanError("Failed Command {}: {}".format(hexlify(cmd), hexlify(data)))
        if data_len == 0:
            raise NoData('NO DATA')

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
            self.socket.settimeout(1)
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

<<<<<<< HEAD
=======
    def setIDFilter(self, id_filter):
        # XXX ????????
        if not isinstance(id_filter, int):
            raise ValueError

        self.can_filter = id_filter

        self.bus.set_filters([{
            'can_id': self.can_filter,
            'can_mask': self.can_mask,
            'extended': True if self.can_filter > 0xfff else False
            }])

>>>>>>> 9b01768... support extended can-ids
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
                    f['id'],# | socket.CAN_EFF_FLAG if self.is_extended else 0,
                    f['mask']))

        self.socket.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_FILTER, flt)

    def getObdVoltage(self):
        if self.watchdog:
            return round(self.watchdog.getVoltage(), 2)

    def calibrateObdVoltage(self, realVoltage):
        if self.watchdog:
            self.watchdog.calibrateVoltage(realVoltage)

    def isCarAvailable(self):
        if 'input_pin' in self.config:
            return True if GPIO.input(self.config['input_pin']) == 0 else False
        elif self.watchdog:
            return self.watchdog.getShutdownFlag() == 0

