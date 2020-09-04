""" Module for the Renault Zoe Z.E.40 """
from time import time
from threading import Thread, Lock
import logging
from .car import Car, ifbu, ifbs
from dongle import NoData

class Zoe(Car):

    def __init__(self, config, dongle, watchdog, gps):
        if config.get('interval') < 1:
            config['interval'] = 1

        Car.__init__(self, config, dongle, watchdog, gps)
        self._dongle.set_protocol('CAN_11_500')
        self._dongle.set_raw_filters_ex([
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
        self._data = self.get_base_data()
        self._data = {}
        self._data_lock = Lock()
        self._last_data = 0
        self._reader_thread = Thread(name="Zoe-Reader-Thread", target=self._reader_thread)
        self._reader_running = False

    def start(self):
        Car.start(self)
        self._reader_running = True
        self._reader_thread.start()

    def stop(self):
        if self._running:
            self._reader_running = False
            self._reader_thread.join()
        Car.stop(self)

    def reader_thread(self):
        while self._reader_running:
            try:
                data = self._dongle.read_raw_frame(1)
                self._last_data = time()

                with self._data_lock:
                    can_id = data['can_id']
                    msg = data['data']

                    if self._log.isEnabledFor(logging.DEBUG):
                        self._log.debug("data can_id(%x) msg(%s)", can_id, msg.hex())

                    if can_id == 0x42e:
                        self._data.update({
                            'SOC_DISPLAY':                  (ifbu(msg[0:2]) >> 3 & 0x1fff) * 0.02,
                            })
                        self._data.update({
                            'dcBatteryVoltage':             (ifbu(msg[3:5]) >> 5 & 0x03ff) * 0.5,
                            'batteryMaxTemperature':        (ifbu(msg[5:7]) >> 5 & 0x007f) - 40,
                            'batteryMinTemperature':        (ifbu(msg[5:7]) >> 5 & 0x007f) - 40,
                            })
                        if 'dcBatteryPower' in self._data:
                            self._data['dcBatteryCurrent'] = \
                                self._data['dcBatteryPower'] / self._data['dcBatteryVoltage']
                    #elif can_id == 0x637:
                    #    self._data.update({
                    #        'cumulativeEnergyCharged':      ifbu(msg[5:7]) >> 4 & 0x0fff,
                    #        })
                    elif can_id == 0x5d7:
                        self._data.update({
                            'odo':                          (ifbu(msg[2:6]) >> 4) * 0.01,
                            })
                    elif can_id == 0x638:
                        self._data.update({
                            'dcBatteryPower':               msg[0] - 80.0,
                            })
                        if 'dcBatteryVoltage' in self._data:
                            self._data['dcBatteryCurrent'] = \
                                self._data['dcBatteryPower'] / self._data['dcBatteryVoltage']
                    #elif can_id == 0x652:
                    #    self._data.update({
                    #        'cumulativeEnergyDischarged':   ifbu(msg[4:6]) & 0x3fff,
                    #        })
                    elif can_id == 0x654:
                        cpc = msg[0] >> 5 & 0x1
                        #ect = msg[2] >> 6 & 0x3

                        self._data.update({
                            'normalChargePort':             int(cpc == 1),
                            })
                    elif can_id == 0x656:
                        self._data.update({
                            'outcan_ideTemp':               msg[6] - 40.0,
                            })
                    elif can_id == 0x658:
                        self._data.update({
                            'charging':                     msg[5] >> 5 & 0x1,
                            'soh':                          msg[4] & 0x7f,
                            })
                    elif can_id == 0x6f8:
                        self._data.update({
                            'auxBatteryVoltage':            msg[2] * 0.0625,
                            })
                    #elif can_id == 0x7bb:
                    #    self._data.update({
                    #        'SOC_BMS':                      msg[] * 0.01,
                    #        })
                    #elif can_id == 0x7ec:
                    #    self._data.update({
                    #        '

            except NoData:
                self._log.debug('NoData')

    def read_dongle(self, data):
        with self._data_lock:
            data.update(self._data)

    def get_base_data(self):
        raise NotImplementedError()

    def get_abrp_model(self):
        raise NotImplementedError()

    def get_evn_model(self):
        raise NotImplementedError()
