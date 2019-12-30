from dongle import *
import can
import math
from pyroute2 import IPRoute
from time import sleep
import logging

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

        self.bus = can.interface.Bus(channel=self.config['port'], bustype='socketcan',
                bitrate=self.config['speed'])
        self.can_id = 0x7df
        self.can_filter = None
        self.can_mask = 0x7ff
        self.is_extended = False
        self.initDongle()

    def sendCommand(self, cmd):
        """
        @cmd: should be hex-encoded
        """
        try:
            cmd_len = len(cmd)
            assert(cmd_len < 8)

            msg_data = bytearray([cmd_len]) + cmd + b"\00" * (7 - cmd_len) # Pad cmd to 8 bytes

            self.cmd_msg = can.Message(extended_id = self.is_extended, arbitration_id = self.can_id, data = msg_data)

            #print(hexlify(cmd),msg_data)
            self.log.debug("{} send message".format(self.cmd_msg))
            self.bus.send(self.cmd_msg)

            data = {}
            data_len = {}

            while True:
                msg = self.bus.recv(0.1)

                if msg == None:
                    break

                can_id = msg.arbitration_id

                if msg.data[0] & 0xf0 == 0x00:
                    self.log.debug("{} single frame".format(msg))
                    data_len[can_id] = msg.data[0] & 0x0f
                    data[can_id] = [bytes(msg.data[1:])]

                elif msg.data[0] & 0xf0 == 0x10:
                    self.log.debug("{} first frame".format(msg))
                    data_len[can_id] = (msg.data[0] & 0x0f) + msg.data[1]
                    lines = math.ceil(data_len[can_id] / 7)
                    data[can_id] = [None] * lines
                    data[can_id][0] = bytes(msg.data[2:])

                    self.log.debug("Send flow control message")
                    flow_msg = can.Message(extended_id = self.is_extended, arbitration_id = cantx, data = [0x30,0,0,0,0,0,0,0])
                    self.bus.send(flow_msg)

                elif msg.data[0] & 0xf0 == 0x20:
                    self.log.debug("{} consecutive frame".format(msg))
                    idx = msg.data[0] & 0x0f
                    data[can_id][idx] = bytes(msg.data[1:])
                    if idx + 1 == data_len[can_id]:
                        # All frames seen, exit loop
                        break

                elif msg.data[0] & 0xf0 == 0x30:
                    raise CanError("Unexpected flow control: {}".format(msg))
                else:
                    raise CanError("Unexpected message: {}".format(msg))

        except OSError as e:
            raise CanError("Failed Command {}: {}".format(cmd.hex(), e))


        if len(data) == 0:
            raise NoData(b'NO DATA')

        #for d in data.keys():
        #    for i,v in enumerate(data[d]):
        #        print("0x{:03x} {}: {}".format(d, i, ' '.join('{:02x}'.format(a) for a in v)))

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

            msg_data = bytearray([cmd_len]) + cmd + b"\00" * (7 - cmd_len) # Pad cmd to 8 bytes

            self.cmd_msg = can.Message(extended_id = self.is_extended, arbitration_id = cantx, data = msg_data)

            self.bus.set_filters([{
                'can_id':   canrx,
                'can_mask': 0x1fffffff if self.is_extended else 0x7ff
                }])

            self.log.debug("{} Sent messsage".format(self.cmd_msg))
            self.bus.send(self.cmd_msg)

            data = None
            data_len = 0
            last_idx = 0

            while True:
                msg = self.bus.recv(0.2)
                self.log.debug(msg)

                if msg == None:
                    break

                if msg.data[0] & 0xf0 == 0x00:
                    self.log.debug("{} single frame".format(msg))
                    data_len = msg.data[0] & 0x0f
                    data = bytes(msg.data[1:data_len+1])
                    break

                elif msg.data[0] & 0xf0 == 0x10:
                    self.log.debug("{} first frame".format(msg))
                    data_len = (msg.data[0] & 0x0f) + msg.data[1]
                    data = bytearray(msg.data[2:])

                    self.log.debug("Send flow control message")
                    flow_msg = can.Message(extended_id = self.is_extended, arbitration_id = cantx, data = [0x30,0,0,0,0,0,0,0])
                    self.bus.send(flow_msg)
                    last_idx = 0

                elif msg.data[0] & 0xf0 == 0x20:
                    self.log.debug("{} consecutive frame".format(msg))
                    idx = msg.data[0] & 0x0f
                    if (last_idx + 1) % 0x10 != idx:
                        raise CanError("Bad frame order: last_idx({}) idx({})".format(last_idx,idx))

                    frame_len = min(7, data_len - len(data))
                    data.extend(msg.data[1:frame_len+1])
                    last_idx = idx

                    if data_len == len(data):
                        break

                elif msg.data[0] & 0xf0 == 0x30:
                    raise CanError("Unexpected flow control: {}".format(msg))
                else:
                    raise CanError("Unexpected message: {}".format(msg))

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
            data_len = {}

            msg = self.bus.recv(timeout)

            if msg == None:
                return None

            data[msg.arbitration_id] = msg.data

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

        ip.link('set', index=ifidx, type='can', txqlen=1, state='up')
        #ip.link('set', index=ifidx, bitrate=500000) # Cannot set bitrate this way ?!?
        ip.close()

    def setAllowLongMessages(self, value):
        return True

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

        self.bus.set_filters([{
            'can_id': self.can_filter,
            'can_mask': self.can_mask,
            'extended': self.is_extended
            }])

    def setCANRxFilter(self, addr):
        if not isinstance(addr, int):
            raise ValueError

        self.can_filter = addr

        self.bus.set_filters([{
            'can_id': self.can_filter,
            'can_mask': self.can_mask,
            'extended': self.is_extended
            }])

    def setFiltersEx(self, filters):
        flt = []
        for f in filters:
            flt.append({
                'can_id': f['id'],
                'can_mask': f['mask'],
                'extended': self.is_extended
                })

        self.bus.set_filters(flt)

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

