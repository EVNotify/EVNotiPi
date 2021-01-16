""" Transmit data to EVNotify and handle notifications """
from time import time, sleep
from threading import Thread, Condition
import logging
import EVNotifyAPI

EVN_SETTINGS_INTERVAL = 300
ABORT_NOTIFICATION_INTERVAL = 60

EXTENDED_FIELDS = {         # value is decimal places
    'auxBatteryVoltage': 1,
    'batteryInletTemperature': 1,
    'batteryMaxTemperature': 1,
    'batteryMinTemperature': 1,
    'cumulativeEnergyCharged': 0,
    'cumulativeEnergyDischarged': 0,
    'charging': 0,
    'normalChargePort': 0,
    'rapidChargePort': 0,
    'dcBatteryCurrent': 2,
    'dcBatteryPower': 2,
    'dcBatteryVoltage': 2,
    'soh': 0,
    'externalTemperature': 1,
    'odo': 0
    }

ARMED = 0
SENT = 1
FAILED = -1


class EVNotify:
    """ Interface to EVNotify. """

    def __init__(self, config, car):
        self._log = logging.getLogger("EVNotiPi/EVNotify")
        self._log.info("Initializing EVNotify")

        self._car = car
        self._config = config
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None

        self._data = []
        self._gps_data = []
        self._data_lock = Condition()

    def start(self):
        """ Start submit thread. """
        self._running = True
        self._thread = Thread(target=self.submit_data, name="EVNotiPi/EVNotify")
        self._thread.start()
        self._car.register_data(self.data_callback)

    def stop(self):
        """ Stop submit thread. """
        self._car.unregister_data(self.data_callback)
        self._running = False
        with self._data_lock:
            self._data_lock.notify()
        self._thread.join()

    def data_callback(self, data):
        """ Callback to be called from 'car'. """
        self._log.debug("Enqeue...")
        with self._data_lock:
            self._data.append(data)
            self._data_lock.notify()

    def submit_data(self):
        """ Thread that submits data to EVNotify in regular intervals. """
        log = self._log
        evn = EVNotifyAPI.EVNotify(self._config['akey'], self._config['token'])

        abort_notification = ARMED
        charging_start_soc = 0
        last_charging = time()
        last_charging_soc = 0
        last_evn_settings_poll = 0
        is_charging = 0
        is_connected = 0
        settings = None
        soc_notification = ARMED
        soc_threshold = self._config.get('soc_threshold', 100)

        log.info("Get settings from backend")
        while self._running and settings is None:
            try:
                settings = evn.getSettings()
            except EVNotifyAPI.CommunicationError as err:
                log.info("Waiting for network connectivity (%s)", err)
                sleep(3)

        while self._running:
            with self._data_lock:
                log.debug('Waiting...')
                self._data_lock.wait(max(10, self._poll_interval))
                now = time()

                # Detect aborted charge
                if ((now - last_charging > ABORT_NOTIFICATION_INTERVAL and
                     charging_start_soc > 0 and 0 < last_charging_soc < soc_threshold and
                     abort_notification is ARMED) or abort_notification is FAILED):
                    log.info("Aborted charge detected, send abort notification now-last_charging(%i) charging_start_soc(%i) last_charging_soc(%i) soc_threshold(%i) abort_notification(%i)",
                             now - last_charging, charging_start_soc, last_charging_soc,
                             soc_threshold, abort_notification)
                    try:
                        evn.sendNotification(True)
                        abort_notification = SENT
                    except EVNotifyAPI.CommunicationError as err:
                        log.error("Communication Error: %s", err)
                        abort_notification = FAILED

                if len(self._data) == 0:
                    continue

                new_data = self._data.copy()
                self._data.clear()

            log.debug("Transmit...")

            avgs = {
                'dcBatteryCurrent': [],
                'dcBatteryPower': [],
                'dcBatteryVoltage': [],
                'speed': [],
                'latitude': [],
                'longitude': [],
                'altitude': [],
            }

            for data in new_data:
                for key, values in avgs.items():
                    if data.get(key, None) is not None:
                        values.append(data[key])

            # Need to copy data here because we update it later
            data = new_data[-1]

            data.update({k: sum(v)/len(v)
                         for k, v in avgs.items() if len(v) > 0})

            try:
                if (data['SOC_DISPLAY'] is not None or
                        data['SOC_BMS'] is not None):
                    evn.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])

                    current_soc = data['SOC_DISPLAY'] or data['SOC_BMS']

                    is_charging = bool(data['charging'])
                    is_connected = bool(data['normalChargePort'] or data['rapidChargePort'])

                    extended_data = {a: round(data[a], EXTENDED_FIELDS[a])
                                     for a in EXTENDED_FIELDS if data[a] is not None}
                    log.debug(extended_data)
                    evn.setExtended(extended_data)

                if data['fix_mode'] > 1:
                    location = {a: data[a]
                                for a in ('latitude', 'longitude', 'speed')}
                    evn.setLocation({'location': location})

                # Notification handling from here on
                if is_charging and now - last_evn_settings_poll > EVN_SETTINGS_INTERVAL:
                    try:
                        settings = evn.getSettings()
                        last_evn_settings_poll = now

                        if 'soc' in settings:
                            new_soc = int(settings['soc'])
                            if new_soc != soc_threshold:
                                soc_threshold = new_soc
                                log.info("New notification threshold: %i",
                                         soc_threshold)

                    except EVNotifyAPI.CommunicationError as err:
                        log.error("Communication error occured %s", err)

                # track charging started
                if is_charging and charging_start_soc == 0:
                    charging_start_soc = current_soc or 0
                elif not is_connected:   # Rearm abort notification
                    charging_start_soc = 0
                    abort_notification = ARMED

                # SoC threshold notification
                if ((is_charging and 0 < last_charging_soc < soc_threshold <= current_soc)
                        or soc_notification is FAILED):
                    log.info("Notification threshold(%i) reached: %i",
                             soc_threshold, current_soc)
                    try:
                        evn.sendNotification()
                        soc_notification = ARMED
                    except EVNotifyAPI.CommunicationError as err:
                        log.info("Communication Error: %s", err)
                        soc_notification = FAILED

                if is_charging:
                    last_charging = now
                    last_charging_soc = current_soc

            except EVNotifyAPI.CommunicationError as err:
                log.info("Communication Error: %s", err)

            # Prime next loop iteration
            if self._running:
                interval = self._poll_interval - (time() - now)
                sleep(max(0, interval))

    def check_thread(self):
        """ Return running state of thread. """
        return self._thread.is_alive()
