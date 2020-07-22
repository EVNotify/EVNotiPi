""" Module for the Renault Zoe Z.E.40 """
from time import time
from threading import Thread
from .car import Car, ifbu, ifbs

class Zoe(Car):

    def __init__(self, config, dongle, watchdog, gps):
        raise Exception('Old ZOE not working yet')
        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._dongle.set_filters_ex([
            {'id': 0x1f6, 'mask': 0x7ff},
            {'id': 0x29a, 'mask': 0x7ff},
            {'id': 0x35c, 'mask': 0x7ff},
            {'id': 0x427, 'mask': 0x7ff},
            {'id': 0x42e, 'mask': 0x7ff},
            {'id': 0x5d7, 'mask': 0x7ff},
            {'id': 0x637, 'mask': 0x7ff},
            {'id': 0x638, 'mask': 0x7ff},
            {'id': 0x652, 'mask': 0x7ff},
            {'id': 0x654, 'mask': 0x7ff},
            {'id': 0x656, 'mask': 0x7ff},
            {'id': 0x658, 'mask': 0x7ff},
            {'id': 0x6f8, 'mask': 0x7ff},
            {'id': 0x7bb, 'mask': 0x7ff},
            ])
        self.data = self.get_base_data()
        self.data = {}
        self.readerthread = Thread(name="Zoe-Reader-Thread", target=self.readerThread)

    def start(self):
        self.running = True
        self.readerthread.start()

    def stop(self):
        if self.running:
            self.running = False
            self.readerthread.join()

    def readerThread(self):
        while self.running:
            now = time()
            self.watchdog = now
            raw = self._dongle.readDataSimple(1)

            if raw is None:
                continue

            with self.datalock.gen_wlock():
                for sid, line in raw.items():
                    if sid == 0x42e:
                        self.data.update({
                            'SOC_DISPLAY':                  (ifbu(line[0:2]) >> 3 & 0x1fff) * 0.02,
                            })
                        self.data.update({
                            'dcBatteryVoltage':             (ifbu(line[3:5]) >> 5 & 0x03ff) * 0.5,
                            'batteryMaxTemperature':        (ifbu(line[5:7]) >> 5 & 0x007f) - 40,
                            'batteryMinTemperature':        (ifbu(line[5:7]) >> 5 & 0x007f) - 40,
                            })
                        if 'dcBatteryPower' in self.data:
                            self.data['dcBatteryCurrent']: self.data['dcBatteryPower'] / self.data['dcBatteryVoltage']
                    #elif sid == 0x637:
                    #    self.data.update({
                    #        'cumulativeEnergyCharged':      ifbu(line[5:7]) >> 4 & 0x0fff,
                    #        })
                    elif sid == 0x5d7:
                        self.data.update({
                            'odo':                          (ifbu(line[2:6]) >> 4) * 0.01,
                            })
                    elif sid == 0x638:
                        self.data.update({
                            'dcBatteryPower':               line[0] - 80.0,
                            })
                        if 'dcBatteryVoltage' in self.data:
                            self.data['dcBatteryCurrent']: self.data['dcBatteryPower'] / self.data['dcBatteryVoltage']
                    #elif sid == 0x652:
                    #    self.data.update({
                    #        'cumulativeEnergyDischarged':   ifbu(line[4:6]) & 0x3fff,
                    #        })
                    elif sid == 0x654:
                        cpc = line[0] >> 5 & 0x1
                        ect = line[2] >> 6 & 0x3

                        self.data.update({
                            'normalChargePort':             1 if cpc == 1 else 0,
                            })
                    elif sid == 0x656:
                        self.data.update({
                            'outsideTemp':                  line[6] - 40.0,
                            })
                    elif sid == 0x658:
                        self.data.update({
                            'charging':                     line[5] >> 5 & 0x1,
                            'soh':                          line[4] & 0x7f,
                            })
                    elif sid == 0x6f8:
                        self.data.update({
                            'auxBatteryVoltage':            line[2] * 0.0625,
                            })
                    #elif sid == 0x7bb:
                    #    self.data.update({
                    #        'SOC_BMS':                      line[] * 0.01,
                    #        })
                    #elif sid == 0x7ec:
                    #    self.data.update({
                    #        '


    def get_base_data(self):
        return {
            "CAPACITY": 22,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 43.0
        }

    def get_abrp_model(self):
        return 'renault:zoe:q210:22:other'

    def get_evn_model(self):
        return 'ZOE'
