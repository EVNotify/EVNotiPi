import serial

class IONIQ_BEV:

    def __init__(self):
        self.command = '2105'
        self.initCMD = [
            'ATD', 'ATZ', 'ATE0', 'ATL0', 'ATS0', 'ATH1', 'AT0', 'ATSTFF', 'ATFE', 'ATSP6', 'ATCRA7EC'
        ]
        # establish serial port
        self.ser = serial.Serial("/dev/rfcomm0", timeout=5)
        self.ser.baudrate=9600

    def init(self):
        for cmd in self.initCMD:
            self.sendCommand(cmd)
        self.requestData()

    def requestData(self):
        self.sendCommand(self.command)

    def sendCommand(self, command):
        self.ser.flushInput()
        cmd = command + '\r\n'
        print(cmd)
        self.ser.write(bytes(command + '\r\n'))
        self.ser.flush()
        if (command == self.command): return
        return self.ser.readline()

    def parseData(self, data):
        if str(data).find('>') and str(data).find('7EC25') and data[-2:] == ['\r', '\r']:
            filtered = [byte.replace('\r', '') for byte in data]
            resolved = ''.join(filtered)
            print(resolved)
            block5 = resolved.find('7EC25')
            soc = (int(resolved[block5-2:block5], 16) / 2)
            print(soc + '%')
            return soc
        return -1

    def getBaseData(self):
        return {
            "CAPACITY": 28,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50
        }