""" Generic implementation of a car module """
from time import time, sleep
from threading import Thread
import logging
from dongle import NoData, CanError


def ifbu(in_bytes):
    """ int from bytes unsigned """
    return int.from_bytes(in_bytes, byteorder='big', signed=False)


def ifbs(in_bytes):
    """ int from bytes signed """
    return int.from_bytes(in_bytes, byteorder='big', signed=True)


def ffbu(in_bytes):
    """ float from int from bytes unsigned """
    return float(int.from_bytes(in_bytes, byteorder='big', signed=False))


def ffbs(in_bytes):
    """ float from int from bytes signed """
    return float(int.from_bytes(in_bytes, byteorder='big', signed=True))


class DataError(Exception):
    """ Problem with data occured """


class Car:
    """ Generic car class """

    def __init__(self, config, dongle, watchdog, gps):
        self._log = logging.getLogger("EVNotiPi/Car")
        self._config = config
        self._dongle = dongle
        self._watchdog = watchdog
        self._gps = gps
        self._poll_interval = config['interval']
        self._thread = None
        self._skip_polling = False
        self._running = False
        self.last_data = 0
        self._data_callbacks = []

    def read_dongle(self, data):
        """ Get raw data from dongle and parse it. """
        raise NotImplementedError()

    def start(self):
        """ Start the poller thread. """
        self._running = True
        self._thread = Thread(target=self.poll_data, name="EVNotiPi/Car")
        self._thread.start()

    def stop(self):
        """ Stop the poller thread. """
        self._running = False
        self._thread.join()

    def poll_data(self):
        """ The poller thread. """
        while self._running:
            now = time()

            # initialize data with required fields; saves all those checks later
            data = {
                'timestamp':    now,
                # Base:
                'SOC_BMS':      None,
                'SOC_DISPLAY':  None,
                # Extended:
                'auxBatteryVoltage':        None,
                'batteryInletTemperature':  None,
                'batteryMaxTemperature':    None,
                'batteryMinTemperature':    None,
                'cumulativeEnergyCharged':  None,
                'cumulativeEnergyDischarged':   None,
                'charging':                 None,
                'normalChargePort':         None,
                'rapidChargePort':          None,
                'dcBatteryCurrent':         None,
                'dcBatteryPower':           None,
                'dcBatteryVoltage':         None,
                'soh':                      None,
                'externalTemperature':      None,
                # Location:
                'latitude':     None,
                'longitude':    None,
                'speed':        None,
                'fix_mode':     0,
            }
            if not self._skip_polling or self._watchdog.is_car_available():
                if self._skip_polling:
                    self._log.info("Resume polling.")
                    self._skip_polling = False
                try:
                    self.read_dongle(data)  # readDongle updates data inplace
                    self.last_data = now
                except CanError as err:
                    self._log.warning(err)
                except NoData:
                    self._log.info("NO DATA")
                    if not self._watchdog.is_car_available():
                        self._log.info("Car off detected. Stop polling until car on.")
                        self._skip_polling = True
                    sleep(1)

            fix = self._gps.fix()
            if fix and fix['mode'] > 1:
                if data['charging'] or data['normalChargePort'] or data['rapidChargePort']:
                    speed = 0.0
                else:
                    speed = fix['speed']

                data.update({
                    'fix_mode':     fix['mode'],
                    'latitude':     fix['latitude'],
                    'longitude':    fix['longitude'],
                    'speed':        speed,
                    'gdop':         fix['gdop'],
                    'pdop':         fix['pdop'],
                    'hdop':         fix['hdop'],
                    'vdop':         fix['vdop'],
                    'tdop':         fix['tdop'],
                    'altitude':     fix['altitude'],
                    'gps_device':   fix['device'],
                })

            if hasattr(self._dongle, 'get_obd_voltage'):
                data.update({
                    'obdVoltage':       self._dongle.get_obd_voltage(),
                })
            elif hasattr(self._watchdog, 'get_voltage'):
                data.update({
                    'obdVoltage':       self._watchdog.get_voltage(),
                })

            if hasattr(self._watchdog, 'get_thresholds'):
                thresholds = self._watchdog.get_thresholds()

                data.update({
                    'startupThreshold':         thresholds['startup'],
                    'shutdownThreshold':        thresholds['shutdown'],
                    'emergencyThreshold':       thresholds['emergency'],
                })

            if self._last_data == now:
                for call_back in self._data_callbacks:
                    call_back(data)

            if self._running:
                if self._poll_interval:
                    runtime = time() - now
                    interval = self._poll_interval - \
                        (runtime if runtime > self._poll_interval else 0)
                    sleep(max(0, interval))

                elif self._skip_polling:
                    sleep(1)

    def register_data(self, callback):
        """ Register a callback that get called with new data. """
        if callback not in self._data_callbacks:
            self._data_callbacks.append(callback)

    def unregister_data(self, callback):
        """ Unregister a callback. """
        self._data_callbacks.remove(callback)

    def check_thread(self):
        """ Return state of thread. """
        return self._thread.is_alive()